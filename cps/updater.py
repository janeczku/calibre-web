# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2018-2019 OzzieIsaacs
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import datetime
import json
import shutil
import threading
import time
import zipfile
from io import BytesIO
from tempfile import gettempdir

import requests
from babel.dates import format_datetime
from flask_babel import gettext as _

from . import constants, logger, config, web_server


log = logger.create()
_REPOSITORY_API_URL = 'https://api.github.com/repos/janeczku/calibre-web'


def is_sha1(sha1):
    if len(sha1) != 40:
        return False
    try:
        int(sha1, 16)
    except ValueError:
        return False
    return True


class Updater(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.paused = False
        # self.pause_cond = threading.Condition(threading.Lock())
        self.can_run = threading.Event()
        self.pause()
        self.status = -1
        self.updateIndex = None
        # self.run()

    def get_current_version_info(self):
        if config.config_updatechannel == constants.UPDATE_STABLE:
            return self._stable_version_info()
        return self._nightly_version_info()

    def get_available_updates(self, request_method, locale):
        if config.config_updatechannel == constants.UPDATE_STABLE:
            return self._stable_available_updates(request_method)
        return self._nightly_available_updates(request_method, locale)

    def do_work(self):
        try:
            self.status = 1
            log.debug(u'Download update file')
            headers = {'Accept': 'application/vnd.github.v3+json'}
            r = requests.get(self._get_request_path(), stream=True, headers=headers, timeout=(10, 600))
            r.raise_for_status()

            self.status = 2
            log.debug(u'Opening zipfile')
            z = zipfile.ZipFile(BytesIO(r.content))
            self.status = 3
            log.debug(u'Extracting zipfile')
            tmp_dir = gettempdir()
            z.extractall(tmp_dir)
            foldername = os.path.join(tmp_dir, z.namelist()[0])[:-1]
            if not os.path.isdir(foldername):
                self.status = 11
                log.info(u'Extracted contents of zipfile not found in temp folder')
                self.pause()
                return False
            self.status = 4
            log.debug(u'Replacing files')
            if self.update_source(foldername, constants.BASE_DIR):
                self.status = 6
                log.debug(u'Preparing restart of server')
                time.sleep(2)
                web_server.stop(True)
                self.status = 7
                time.sleep(2)
                return True
            else:
                self.status = 13

        except requests.exceptions.HTTPError as ex:
            log.error(u'HTTP Error %s', ex)
            self.status = 8
        except requests.exceptions.ConnectionError:
            log.error(u'Connection error')
            self.status = 9
        except requests.exceptions.Timeout:
            log.error(u'Timeout while establishing connection')
            self.status = 10
        except (requests.exceptions.RequestException, zipfile.BadZipFile):
            self.status = 11
            log.error(u'General error')
        except (IOError, OSError) as ex:
            self.status = 12
            log.error(u'Possible Reason for error: update file could not be saved in temp dir')
            log.debug_or_exception(ex)
        self.pause()
        return False

    def run(self):
        while True:
            self.can_run.wait()
            if self.status > -1:
                if self.do_work():
                    break   # stop loop and end thread for restart
            else:
                break

    def pause(self):
        self.can_run.clear()

    # should just resume the thread
    def resume(self):
        self.can_run.set()

    def stop(self):
        self.status = -2
        self.can_run.set()

    def get_update_status(self):
        return self.status

    @classmethod
    def file_to_list(cls, filelist):
        return [x.strip() for x in open(filelist, 'r') if not x.startswith('#EXT')]

    @classmethod
    def one_minus_two(cls, one, two):
        return [x for x in one if x not in set(two)]

    @classmethod
    def reduce_dirs(cls, delete_files, new_list):
        new_delete = []
        for filename in delete_files:
            parts = filename.split(os.sep)
            sub = ''
            for part in parts:
                sub = os.path.join(sub, part)
                if sub == '':
                    sub = os.sep
                count = 0
                for song in new_list:
                    if song.startswith(sub):
                        count += 1
                        break
                if count == 0:
                    if sub != '\\':
                        new_delete.append(sub)
                    break
        return list(set(new_delete))

    @classmethod
    def reduce_files(cls, remove_items, exclude_items):
        rf = []
        for item in remove_items:
            if not item.startswith(exclude_items):
                rf.append(item)
        return rf

    @classmethod
    def check_permissions(cls, root_src_dir, root_dst_dir):
        access = True
        remove_path = len(root_src_dir) + 1
        for src_dir, __, files in os.walk(root_src_dir):
            root_dir = os.path.join(root_dst_dir, src_dir[remove_path:])
            # Skip non existing folders on check
            if not os.path.isdir(root_dir): # root_dir.lstrip(os.sep).startswith('.') or
                continue
            if not os.access(root_dir, os.R_OK|os.W_OK):
                log.debug("Missing permissions for {}".format(root_dir))
                access = False
            for file_ in files:
                curr_file = os.path.join(root_dir, file_)
                # Skip non existing files on check
                if not os.path.isfile(curr_file): # or curr_file.startswith('.'):
                    continue
                if not os.access(curr_file, os.R_OK|os.W_OK):
                    log.debug("Missing permissions for {}".format(curr_file))
                    access = False
        return access

    @classmethod
    def moveallfiles(cls, root_src_dir, root_dst_dir):
        new_permissions = os.stat(root_dst_dir)
        log.debug('Performing Update on OS-System: %s', sys.platform)
        change_permissions = not (sys.platform == "win32" or sys.platform == "darwin")
        for src_dir, __, files in os.walk(root_src_dir):
            dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
            if not os.path.exists(dst_dir):
                try:
                    os.makedirs(dst_dir)
                    log.debug('Create directory: {}', dst_dir)
                except OSError as e:
                    log.error('Failed creating folder: {} with error {}'.format(dst_dir, e))
                if change_permissions:
                    try:
                        os.chown(dst_dir, new_permissions.st_uid, new_permissions.st_gid)
                    except OSError as e:
                        old_permissions = os.stat(dst_dir)
                        log.error('Failed changing permissions of %s. Before: %s:%s After %s:%s error: %s',
                                  dst_dir, old_permissions.st_uid, old_permissions.st_gid,
                                  new_permissions.st_uid, new_permissions.st_gid, e)
            for file_ in files:
                src_file = os.path.join(src_dir, file_)
                dst_file = os.path.join(dst_dir, file_)
                if os.path.exists(dst_file):
                    if change_permissions:
                        permission = os.stat(dst_file)
                    try:
                        os.remove(dst_file)
                        log.debug('Remove file before copy: %s', dst_file)
                    except OSError as e:
                        log.error('Failed removing file: {} with error {}'.format(dst_file, e))
                else:
                    if change_permissions:
                        permission = new_permissions
                try:
                    shutil.move(src_file, dst_dir)
                    log.debug('Move File %s to %s', src_file, dst_dir)
                except OSError as ex:
                    log.error('Failed moving file from {} to {} with error {}'.format(src_file, dst_dir, ex))
                if change_permissions:
                    try:
                        os.chown(dst_file, permission.st_uid, permission.st_gid)
                    except OSError as e:
                        old_permissions = os.stat(dst_file)
                        log.error('Failed changing permissions of %s. Before: %s:%s After %s:%s error: %s',
                                  dst_file, old_permissions.st_uid, old_permissions.st_gid,
                                  permission.st_uid, permission.st_gid, e)
        return

    def update_source(self, source, destination):
        # destination files
        old_list = list()
        exclude = (
            os.sep + 'app.db', os.sep + 'calibre-web.log1', os.sep + 'calibre-web.log2', os.sep + 'gdrive.db',
            os.sep + 'vendor', os.sep + 'calibre-web.log', os.sep + '.git', os.sep + 'client_secrets.json',
            os.sep + 'gdrive_credentials', os.sep + 'settings.yaml', os.sep + 'venv', os.sep + 'virtualenv',
            os.sep + 'access.log', os.sep + 'access.log1', os.sep + 'access.log2',
            os.sep + '.calibre-web.log.swp', os.sep + '_sqlite3.so', os.sep + 'cps' + os.sep + '.HOMEDIR',
            os.sep + 'gmail.json'
        )
        additional_path = self.is_venv()
        if additional_path:
            exclude = exclude + (additional_path,)

        # check if we are in a package, rename cps.py to __init__.py
        if constants.HOME_CONFIG:
            shutil.move(os.path.join(source, 'cps.py'), os.path.join(source, '__init__.py'))

        for root, dirs, files in os.walk(destination, topdown=True):
            for name in files:
                old_list.append(os.path.join(root, name).replace(destination, ''))
            for name in dirs:
                old_list.append(os.path.join(root, name).replace(destination, ''))
        # source files
        new_list = list()
        for root, dirs, files in os.walk(source, topdown=True):
            for name in files:
                new_list.append(os.path.join(root, name).replace(source, ''))
            for name in dirs:
                new_list.append(os.path.join(root, name).replace(source, ''))

        delete_files = self.one_minus_two(old_list, new_list)

        rf = self.reduce_files(delete_files, exclude)

        remove_items = self.reduce_dirs(rf, new_list)

        if self.check_permissions(source, destination):
            self.moveallfiles(source, destination)

            for item in remove_items:
                item_path = os.path.join(destination, item[1:])
                if os.path.isdir(item_path):
                    log.debug("Delete dir %s", item_path)
                    shutil.rmtree(item_path, ignore_errors=True)
                else:
                    try:
                        os.remove(item_path)
                        log.debug("Delete file %s", item_path)
                    except OSError:
                        log.debug("Could not remove: %s", item_path)
            shutil.rmtree(source, ignore_errors=True)
            return True
        else:
            log.debug("Permissions missing for update")
            return False

    @staticmethod
    def is_venv():
        if (hasattr(sys, 'real_prefix')) or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            return os.sep + os.path.relpath(sys.prefix, constants.BASE_DIR)
        else:
            return False

    @classmethod
    def _nightly_version_info(cls):
        if is_sha1(constants.NIGHTLY_VERSION[0]) and len(constants.NIGHTLY_VERSION[1]) > 0:
            log.debug("Nightly version: {}, {}".format(constants.NIGHTLY_VERSION[0], constants.NIGHTLY_VERSION[1]))
            return {'version': constants.NIGHTLY_VERSION[0], 'datetime': constants.NIGHTLY_VERSION[1]}
        return False

    @classmethod
    def _stable_version_info(cls):
        log.debug("Stable version: {}".format(constants.STABLE_VERSION))
        return constants.STABLE_VERSION  # Current version

    @staticmethod
    def _populate_parent_commits(update_data, status, locale, tz, parents):
        try:
            parent_commit = update_data['parents'][0]
            # limit the maximum search depth
            remaining_parents_cnt = 10
        except (IndexError, KeyError):
            remaining_parents_cnt = None

        if remaining_parents_cnt is not None:
            while True:
                if remaining_parents_cnt == 0:
                    break

                # check if we are more than one update behind if so, go up the tree
                if parent_commit['sha'] != status['current_commit_hash']:
                    try:
                        headers = {'Accept': 'application/vnd.github.v3+json'}
                        r = requests.get(parent_commit['url'], headers=headers, timeout=10)
                        r.raise_for_status()
                        parent_data = r.json()

                        parent_commit_date = datetime.datetime.strptime(
                            parent_data['committer']['date'], '%Y-%m-%dT%H:%M:%SZ') - tz
                        parent_commit_date = format_datetime(
                            parent_commit_date, format='short', locale=locale)

                        parents.append([parent_commit_date,
                                        parent_data['message'].replace('\r\n', '<p>').replace('\n', '<p>')])
                        parent_commit = parent_data['parents'][0]
                        remaining_parents_cnt -= 1
                    except Exception:
                        # it isn't crucial if we can't get information about the parent
                        break
                else:
                    # parent is our current version
                    break
        return parents

    @staticmethod
    def _load_nightly_data(repository_url, commit, status):
        update_data = dict()
        try:
            headers = {'Accept': 'application/vnd.github.v3+json'}
            r = requests.get(repository_url + '/git/commits/' + commit['object']['sha'],
                             headers=headers,
                             timeout=10)
            r.raise_for_status()
            update_data = r.json()
        except requests.exceptions.HTTPError as e:
            status['message'] = _(u'HTTP Error') + ' ' + str(e)
        except requests.exceptions.ConnectionError:
            status['message'] = _(u'Connection error')
        except requests.exceptions.Timeout:
            status['message'] = _(u'Timeout while establishing connection')
        except (requests.exceptions.RequestException, ValueError):
            status['message'] = _(u'General error')
        return status, update_data

    def _nightly_available_updates(self, request_method, locale):
        tz = datetime.timedelta(seconds=time.timezone if (time.localtime().tm_isdst == 0) else time.altzone)
        if request_method == "GET":
            repository_url = _REPOSITORY_API_URL
            status, commit = self._load_remote_data(repository_url + '/git/refs/heads/master')
            parents = []
            if status['message'] != '':
                return json.dumps(status)
            if 'object' not in commit or 'url' not in commit['object']:
                status['message'] = _(u'Unexpected data while reading update information')
                return json.dumps(status)
            try:
                if commit['object']['sha'] == status['current_commit_hash']:
                    status.update({
                        'update': False,
                        'success': True,
                        'message': _(u'No update available. You already have the latest version installed')
                    })
                    return json.dumps(status)
            except (TypeError, KeyError):
                status['message'] = _(u'Unexpected data while reading update information')
                return json.dumps(status)

            # a new update is available
            status['update'] = True
            status, update_data = self._load_nightly_data(repository_url, commit, status)

            if status['message'] != '':
                return json.dumps(status)

            # if 'committer' in update_data and 'message' in update_data:
            try:
                log.debug("A new update is available.")
                status['success'] = True
                status['message'] = _(
                    u'A new update is available. Click on the button below to update to the latest version.')

                new_commit_date = datetime.datetime.strptime(
                    update_data['committer']['date'], '%Y-%m-%dT%H:%M:%SZ') - tz
                parents.append(
                    [
                        format_datetime(new_commit_date, format='short', locale=locale),
                        update_data['message'],
                        update_data['sha']
                    ]
                )
                # it only makes sense to analyze the parents if we know the current commit hash
                if status['current_commit_hash'] != '':
                    parents = self._populate_parent_commits(update_data, status, locale, tz, parents)
                status['history'] = parents[::-1]
            except (IndexError, KeyError):
                status['success'] = False
                status['message'] = _(u'Could not fetch update information')
                log.error("Could not fetch update information")
            return json.dumps(status)
        return ''

    def _stable_updater_set_status(self, i, newer, status, parents, commit):
        if i == -1 and newer == False:
            status.update({
                'update': True,
                'success': True,
                'message': _(
                    u'Click on the button below to update to the latest stable version.'),
                'history': parents
            })
            self.updateFile = commit[0]['zipball_url']
        elif i == -1 and newer == True:
            status.update({
                'update': True,
                'success': True,
                'message': _(u'A new update is available. Click on the button below to '
                             u'update to version: %(version)s', version=commit[0]['tag_name']),
                'history': parents
            })
            self.updateFile = commit[0]['zipball_url']
        return status

    def _stable_updater_parse_major_version(self, commit, i, parents, current_version, status):
        if int(commit[i + 1]['tag_name'].split('.')[1]) == current_version[1]:
            parents.append([commit[i]['tag_name'],
                            commit[i]['body'].replace('\r\n', '<p>').replace('\n', '<p>')])
            status.update({
                'update': True,
                'success': True,
                'message': _(u'A new update is available. Click on the button below to '
                             u'update to version: %(version)s', version=commit[i]['tag_name']),
                'history': parents
            })
            self.updateFile = commit[i]['zipball_url']
        else:
            parents.append([commit[i + 1]['tag_name'],
                            commit[i + 1]['body'].replace('\r\n', '<p>').replace('\n', '<p>')])
            status.update({
                'update': True,
                'success': True,
                'message': _(u'A new update is available. Click on the button below to '
                             u'update to version: %(version)s', version=commit[i + 1]['tag_name']),
                'history': parents
            })
            self.updateFile = commit[i + 1]['zipball_url']
        return status, parents

    def _stable_available_updates(self, request_method):
        if request_method == "GET":
            parents = []
            # repository_url = 'https://api.github.com/repos/flatpak/flatpak/releases'  # test URL
            repository_url = _REPOSITORY_API_URL + '/releases?per_page=100'
            status, commit = self._load_remote_data(repository_url)
            if status['message'] != '':
                return json.dumps(status)
            if not commit:
                status['success'] = True
                status['message'] = _(u'No release information available')
                return json.dumps(status)
            version = status['current_commit_hash']
            current_version = status['current_commit_hash'].split('.')

            # we are already on newest version, no update available
            if 'tag_name' not in commit[0]:
                status['message'] = _(u'Unexpected data while reading update information')
                log.error("Unexpected data while reading update information")
                return json.dumps(status)
            if commit[0]['tag_name'] == version:
                status.update({
                    'update': False,
                    'success': True,
                    'message': _(u'No update available. You already have the latest version installed')
                })
                return json.dumps(status)

            i = len(commit) - 1
            newer = False
            while i >= 0:
                if 'tag_name' not in commit[i] or 'body' not in commit[i] or 'zipball_url' not in commit[i]:
                    status['message'] = _(u'Unexpected data while reading update information')
                    return json.dumps(status)
                major_version_update = int(commit[i]['tag_name'].split('.')[0])
                minor_version_update = int(commit[i]['tag_name'].split('.')[1])
                patch_version_update = int(commit[i]['tag_name'].split('.')[2])

                current_version[0] = int(current_version[0])
                current_version[1] = int(current_version[1])
                try:
                    current_version[2] = int(current_version[2])
                except ValueError:
                    current_version[2] = int(current_version[2].split(' ')[0])-1

                # Check if major versions are identical search for newest non equal commit and update to this one
                if major_version_update == current_version[0]:
                    if (minor_version_update == current_version[1] and
                            patch_version_update > current_version[2]) or \
                            minor_version_update > current_version[1]:
                        parents.append([commit[i]['tag_name'], commit[i]['body'].replace('\r\n', '<p>')])
                        newer = True
                    i -= 1
                    continue
                if major_version_update < current_version[0]:
                    i -= 1
                    continue
                if major_version_update > current_version[0]:
                    # found update update to last version before major update, unless current version is on last version
                    # before major update
                    if i == (len(commit) - 1):
                        i -= 1
                    status, parents = self._stable_updater_parse_major_version(commit,
                                                                               i,
                                                                               parents,
                                                                               current_version,
                                                                               status)
                    break

            status = self._stable_updater_set_status(i, newer, status, parents, commit)
        return json.dumps(status)

    def _get_request_path(self):
        if config.config_updatechannel == constants.UPDATE_STABLE:
            return self.updateFile
        return _REPOSITORY_API_URL + '/zipball/master'

    def _load_remote_data(self, repository_url):
        status = {
            'update': False,
            'success': False,
            'message': '',
            'current_commit_hash': ''
        }
        commit = None
        version = self.get_current_version_info()
        if version is False:
            status['current_commit_hash'] = _(u'Unknown')
        else:
            status['current_commit_hash'] = version['version']
        try:
            headers = {'Accept': 'application/vnd.github.v3+json'}
            r = requests.get(repository_url, headers=headers, timeout=10)
            commit = r.json()
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if commit:
                if 'message' in commit:
                    status['message'] = _(u'HTTP Error') + ': ' + commit['message']
            else:
                status['message'] = _(u'HTTP Error') + ': ' + str(e)
        except requests.exceptions.ConnectionError:
            status['message'] = _(u'Connection error')
        except requests.exceptions.Timeout:
            status['message'] = _(u'Timeout while establishing connection')
        except (requests.exceptions.RequestException, ValueError):
            status['message'] = _(u'General error')
        log.debug('Updater status: {}'.format(status['message'] or "OK"))
        return status, commit
