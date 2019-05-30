#!/usr/bin/env python
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

import threading
import zipfile
import requests
import re
import logging
import server
import time
from io import BytesIO
import os
import sys
import shutil
from ub import config, UPDATE_STABLE
from tempfile import gettempdir
import datetime
import json
from flask_babel import gettext as _
from babel.dates import format_datetime
import web


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
        self.status = -1
        self.updateIndex = None

    def get_current_version_info(self):
        if config.get_update_channel == UPDATE_STABLE:
            return self._stable_version_info()
        else:
            return self._nightly_version_info()

    def get_available_updates(self, request_method):
        if config.get_update_channel == UPDATE_STABLE:
            return self._stable_available_updates(request_method)
        else:
            return self._nightly_available_updates(request_method)

    def run(self):
        try:
            self.status = 1
            r = requests.get(self._get_request_path(), stream=True)
            r.raise_for_status()

            self.status = 2
            z = zipfile.ZipFile(BytesIO(r.content))
            self.status = 3
            tmp_dir = gettempdir()
            z.extractall(tmp_dir)
            foldername = os.path.join(tmp_dir, z.namelist()[0])[:-1]
            if not os.path.isdir(foldername):
                self.status = 11
                logging.getLogger('cps.web').info(u'Extracted contents of zipfile not found in temp folder')
                return
            self.status = 4
            self.update_source(foldername, config.get_main_dir)
            self.status = 6
            time.sleep(2)
            server.Server.setRestartTyp(True)
            server.Server.stopServer()
            self.status = 7
            time.sleep(2)
        except requests.exceptions.HTTPError as ex:
            logging.getLogger('cps.web').info( u'HTTP Error' + ' ' + str(ex))
            self.status = 8
        except requests.exceptions.ConnectionError:
            logging.getLogger('cps.web').info(u'Connection error')
            self.status = 9
        except requests.exceptions.Timeout:
            logging.getLogger('cps.web').info(u'Timeout while establishing connection')
            self.status = 10
        except requests.exceptions.RequestException:
            self.status = 11
            logging.getLogger('cps.web').info(u'General error')

    def get_update_status(self):
        return self.status

    @classmethod
    def file_to_list(self, filelist):
        return [x.strip() for x in open(filelist, 'r') if not x.startswith('#EXT')]

    @classmethod
    def one_minus_two(self, one, two):
        return [x for x in one if x not in set(two)]

    @classmethod
    def reduce_dirs(self, delete_files, new_list):
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
    def reduce_files(self, remove_items, exclude_items):
        rf = []
        for item in remove_items:
            if not item.startswith(exclude_items):
                rf.append(item)
        return rf

    @classmethod
    def moveallfiles(self, root_src_dir, root_dst_dir):
        change_permissions = True
        if sys.platform == "win32" or sys.platform == "darwin":
            change_permissions = False
        else:
            logging.getLogger('cps.web').debug('Update on OS-System : ' + sys.platform)
            new_permissions = os.stat(root_dst_dir)
            # print new_permissions
        for src_dir, __, files in os.walk(root_src_dir):
            dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
                logging.getLogger('cps.web').debug('Create-Dir: '+dst_dir)
                if change_permissions:
                    # print('Permissions: User '+str(new_permissions.st_uid)+' Group '+str(new_permissions.st_uid))
                    os.chown(dst_dir, new_permissions.st_uid, new_permissions.st_gid)
            for file_ in files:
                src_file = os.path.join(src_dir, file_)
                dst_file = os.path.join(dst_dir, file_)
                if os.path.exists(dst_file):
                    if change_permissions:
                        permission = os.stat(dst_file)
                    logging.getLogger('cps.web').debug('Remove file before copy: '+dst_file)
                    os.remove(dst_file)
                else:
                    if change_permissions:
                        permission = new_permissions
                shutil.move(src_file, dst_dir)
                logging.getLogger('cps.web').debug('Move File '+src_file+' to '+dst_dir)
                if change_permissions:
                    try:
                        os.chown(dst_file, permission.st_uid, permission.st_gid)
                    except (Exception) as e:
                        # ex = sys.exc_info()
                        old_permissions = os.stat(dst_file)
                        logging.getLogger('cps.web').debug('Fail change permissions of ' + str(dst_file) + '. Before: '
                            + str(old_permissions.st_uid) + ':' + str(old_permissions.st_gid) + ' After: '
                            + str(permission.st_uid) + ':' + str(permission.st_gid) + ' error: '+str(e))
        return

    def update_source(self, source, destination):
        # destination files
        old_list = list()
        exclude = (
            os.sep + 'app.db', os.sep + 'calibre-web.log1', os.sep + 'calibre-web.log2', os.sep + 'gdrive.db',
            os.sep + 'vendor', os.sep + 'calibre-web.log', os.sep + '.git', os.sep +'client_secrets.json',
            os.sep + 'gdrive_credentials', os.sep + 'settings.yaml')
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

        self.moveallfiles(source, destination)

        for item in remove_items:
            item_path = os.path.join(destination, item[1:])
            if os.path.isdir(item_path):
                logging.getLogger('cps.web').debug("Delete dir " + item_path)
                shutil.rmtree(item_path, ignore_errors=True)
            else:
                try:
                    logging.getLogger('cps.web').debug("Delete file " + item_path)
                    # log_from_thread("Delete file " + item_path)
                    os.remove(item_path)
                except Exception:
                    logging.getLogger('cps.web').debug("Could not remove:" + item_path)
        shutil.rmtree(source, ignore_errors=True)

    def _nightly_version_info(self):
        content = {}
        content[0] = '$Format:%H$'
        content[1] = '$Format:%cI$'
        # content[0] = 'bb7d2c6273ae4560e83950d36d64533343623a57'
        # content[1] = '2018-09-09T10:13:08+02:00'
        if is_sha1(content[0]) and len(content[1]) > 0:
            return {'version': content[0], 'datetime': content[1]}
        return False

    def _stable_version_info(self):
        return {'version': '0.6.4 Beta'} # Current version

    def _nightly_available_updates(self, request_method):
        tz = datetime.timedelta(seconds=time.timezone if (time.localtime().tm_isdst == 0) else time.altzone)
        if request_method == "GET":
            repository_url = 'https://api.github.com/repos/janeczku/calibre-web'
            status, commit = self._load_remote_data(repository_url +'/git/refs/heads/master')
            parents = []
            if status['message'] != '':
                return json.dumps(status)
            if 'object' not in commit:
                status['message'] = _(u'Unexpected data while reading update information')
                return json.dumps(status)

            if commit['object']['sha'] == status['current_commit_hash']:
                status.update({
                    'update': False,
                    'success': True,
                    'message': _(u'No update available. You already have the latest version installed')
                })
                return json.dumps(status)

            # a new update is available
            status['update'] = True

            try:
                r = requests.get(repository_url + '/git/commits/' + commit['object']['sha'])
                r.raise_for_status()
                update_data = r.json()
            except requests.exceptions.HTTPError as e:
                status['error'] = _(u'HTTP Error') + ' ' + str(e)
            except requests.exceptions.ConnectionError:
                status['error'] = _(u'Connection error')
            except requests.exceptions.Timeout:
                status['error'] = _(u'Timeout while establishing connection')
            except requests.exceptions.RequestException:
                status['error'] = _(u'General error')

            if status['message'] != '':
                return json.dumps(status)

            if 'committer' in update_data and 'message' in update_data:
                status['success'] = True
                status['message'] = _(
                    u'A new update is available. Click on the button below to update to the latest version.')

                new_commit_date = datetime.datetime.strptime(
                    update_data['committer']['date'], '%Y-%m-%dT%H:%M:%SZ') - tz
                parents.append(
                    [
                        format_datetime(new_commit_date, format='short', locale=web.get_locale()),
                        update_data['message'],
                        update_data['sha']
                    ]
                )

                # it only makes sense to analyze the parents if we know the current commit hash
                if status['current_commit_hash'] != '':
                    try:
                        parent_commit = update_data['parents'][0]
                        # limit the maximum search depth
                        remaining_parents_cnt = 10
                    except IndexError:
                        remaining_parents_cnt = None

                    if remaining_parents_cnt is not None:
                        while True:
                            if remaining_parents_cnt == 0:
                                break

                            # check if we are more than one update behind if so, go up the tree
                            if parent_commit['sha'] != status['current_commit_hash']:
                                try:
                                    r = requests.get(parent_commit['url'])
                                    r.raise_for_status()
                                    parent_data = r.json()

                                    parent_commit_date = datetime.datetime.strptime(
                                        parent_data['committer']['date'], '%Y-%m-%dT%H:%M:%SZ') - tz
                                    parent_commit_date = format_datetime(
                                        parent_commit_date, format='short', locale=web.get_locale())

                                    parents.append([parent_commit_date,
                                                    parent_data['message'].replace('\r\n','<p>').replace('\n','<p>')])
                                    parent_commit = parent_data['parents'][0]
                                    remaining_parents_cnt -= 1
                                except Exception:
                                    # it isn't crucial if we can't get information about the parent
                                    break
                            else:
                                # parent is our current version
                                break

            else:
                status['success'] = False
                status['message'] = _(u'Could not fetch update information')

            # a new update is available
            status['update'] = True
            if 'body' in commit:
                status['success'] = True
                status['message'] = _(
                    u'A new update is available. Click on the button below to update to the latest version.')

                new_commit_date = datetime.datetime.strptime(
                    commit['committer']['date'], '%Y-%m-%dT%H:%M:%SZ') - tz
                parents.append(
                    [
                        format_datetime(new_commit_date, format='short', locale=web.get_locale()),
                        commit['message'],
                        commit['sha']
                    ]
                )

                # it only makes sense to analyze the parents if we know the current commit hash
                if status['current_commit_hash'] != '':
                    try:
                        parent_commit = commit['parents'][0]
                        # limit the maximum search depth
                        remaining_parents_cnt = 10
                    except IndexError:
                        remaining_parents_cnt = None

                    if remaining_parents_cnt is not None:
                        while True:
                            if remaining_parents_cnt == 0:
                                break

                            # check if we are more than one update behind if so, go up the tree
                            if commit['sha'] != status['current_commit_hash']:
                                try:
                                    r = requests.get(parent_commit['url'])
                                    r.raise_for_status()
                                    parent_data = r.json()

                                    parent_commit_date = datetime.datetime.strptime(
                                        parent_data['committer']['date'], '%Y-%m-%dT%H:%M:%SZ') - tz
                                    parent_commit_date = format_datetime(
                                        parent_commit_date, format='short', locale=web.get_locale())

                                    parents.append([parent_commit_date, parent_data['message'], parent_data['sha']])
                                    parent_commit = parent_data['parents'][0]
                                    remaining_parents_cnt -= 1
                                except Exception:
                                    # it isn't crucial if we can't get information about the parent
                                    break
                            else:
                                # parent is our current version
                                break
            status['history'] = parents[::-1]
            return json.dumps(status)
        return ''

    def _stable_available_updates(self, request_method):
        if request_method == "GET":
            parents = []
            # repository_url = 'https://api.github.com/repos/flatpak/flatpak/releases'  # test URL
            repository_url = 'https://api.github.com/repos/janeczku/calibre-web/releases'
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
                return json.dumps(status)
            if commit[0]['tag_name'] == version:
                status.update({
                    'update': False,
                    'success': True,
                    'message': _(u'No update available. You already have the latest version installed')
                })
                return json.dumps(status)

            i = len(commit) - 1
            while i >= 0:
                if 'tag_name' not in commit[i] or 'body' not in commit[i]:
                    status['message'] = _(u'Unexpected data while reading update information')
                    return json.dumps(status)
                major_version_update = int(commit[i]['tag_name'].split('.')[0])
                minor_version_update = int(commit[i]['tag_name'].split('.')[1])
                patch_version_update = int(commit[i]['tag_name'].split('.')[2])

                # Check if major versions are identical search for newest nonenqual commit and update to this one
                if major_version_update == int(current_version[0]):
                    if (minor_version_update == int(current_version[1]) and
                            patch_version_update > int(current_version[2])) or \
                            minor_version_update > int(current_version[1]):
                        parents.append([commit[i]['tag_name'],commit[i]['body'].replace('\r\n', '<p>')])
                    i -= 1
                    continue
                if major_version_update < int(current_version[0]):
                    i -= 1
                    continue
                if major_version_update > int(current_version[0]):
                    # found update update to last version before major update, unless current version is on last version
                    # before major update
                    if commit[i+1]['tag_name'].split('.')[1] == current_version[1]:
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
                        status.update({
                            'update': True,
                            'success': True,
                            'message': _(u'A new update is available. Click on the button below to '
                                         u'update to version: %(version)s', version=commit[i]['tag_name']),
                            'history': parents
                        })
                        self.updateFile = commit[i +1]['zipball_url']
                    break
            if i == -1:
                status.update({
                    'update': True,
                    'success': True,
                    'message': _(
                        u'A new update is available. Click on the button below to update to the latest version.'),
                    'history': parents
                })
                self.updateFile = commit[0]['zipball_url']
        return json.dumps(status)

    def _get_request_path(self):
        if config.get_update_channel == UPDATE_STABLE:
            return self.updateFile
        else:
            return 'https://api.github.com/repos/janeczku/calibre-web/zipball/master'

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
            r = requests.get(repository_url)
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
        except requests.exceptions.RequestException:
            status['message'] = _(u'General error')

        return status, commit


updater_thread = Updater()
