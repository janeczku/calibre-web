# -*- coding: utf-8 -*-

#  This file is part of the Calibre-Web (https://github.com/janeczku/calibre-web)
#    Copyright (C) 2012-2019 janeczku, OzzieIsaacs, andrerfcsantos, idalin
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
import errno
import signal
import socket

try:
    from gevent.pywsgi import WSGIServer
    from .gevent_wsgi import MyWSGIHandler
    from gevent.pool import Pool
    from gevent.socket import socket as GeventSocket
    from gevent import __version__ as _version
    from greenlet import GreenletExit
    import ssl
    VERSION = 'Gevent ' + _version
    _GEVENT = True
except ImportError:
    from .tornado_wsgi import MyWSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop
    from tornado import netutil
    from tornado import version as _version
    VERSION = 'Tornado ' + _version
    _GEVENT = False

from . import logger


log = logger.create()


def _readable_listen_address(address, port):
    if ':' in address:
        address = "[" + address + "]"
    return '%s:%s' % (address, port)


class WebServer(object):

    def __init__(self):
        signal.signal(signal.SIGINT, self._killServer)
        signal.signal(signal.SIGTERM, self._killServer)

        self.wsgiserver = None
        self.access_logger = None
        self.restart = False
        self.app = None
        self.listen_address = None
        self.listen_port = None
        self.unix_socket_file = None
        self.ssl_args = None

    def init_app(self, application, config):
        self.app = application
        self.listen_address = config.get_config_ipaddress()
        self.listen_port = config.config_port

        if config.config_access_log:
            log_name = "gevent.access" if _GEVENT else "tornado.access"
            formatter = logger.ACCESS_FORMATTER_GEVENT if _GEVENT else logger.ACCESS_FORMATTER_TORNADO
            self.access_logger, logfile = logger.create_access_log(config.config_access_logfile, log_name, formatter)
            if logfile != config.config_access_logfile:
                log.warning("Accesslog path %s not valid, falling back to default", config.config_access_logfile)
                config.config_access_logfile = logfile
                config.save()
        else:
            if not _GEVENT:
                logger.get('tornado.access').disabled = True

        certfile_path = config.get_config_certfile()
        keyfile_path = config.get_config_keyfile()
        if certfile_path and keyfile_path:
            if os.path.isfile(certfile_path) and os.path.isfile(keyfile_path):
                self.ssl_args = dict(certfile=certfile_path, keyfile=keyfile_path)
            else:
                log.warning('The specified paths for the ssl certificate file and/or key file seem to be broken. '
                            'Ignoring ssl.')
                log.warning('Cert path: %s', certfile_path)
                log.warning('Key path:  %s', keyfile_path)

    @staticmethod
    def _make_gevent_socket_activated():
        # Reuse an already open socket on fd=SD_LISTEN_FDS_START
        SD_LISTEN_FDS_START = 3
        return GeventSocket(fileno=SD_LISTEN_FDS_START)

    def _prepare_unix_socket(self, socket_file):
        # the socket file must not exist prior to bind()
        if os.path.exists(socket_file):
            # avoid nuking regular files and symbolic links (could be a mistype or security issue)
            if os.path.isfile(socket_file) or os.path.islink(socket_file):
                raise OSError(errno.EEXIST, os.strerror(errno.EEXIST), socket_file)
            os.remove(socket_file)

        self.unix_socket_file = socket_file

    def _make_gevent_listener(self):
        if os.name != 'nt':
            socket_activated = os.environ.get("LISTEN_FDS")
            if socket_activated:
                sock = self._make_gevent_socket_activated()
                sock_info = sock.getsockname()
                return sock, "systemd-socket:" + _readable_listen_address(sock_info[0], sock_info[1])
            unix_socket_file = os.environ.get("CALIBRE_UNIX_SOCKET")
            if unix_socket_file:
                self._prepare_unix_socket(unix_socket_file)
                unix_sock = WSGIServer.get_listener(unix_socket_file, family=socket.AF_UNIX)
                # ensure current user and group have r/w permissions, no permissions for other users
                # this way the socket can be shared in a semi-secure manner
                # between the user running calibre-web and the user running the fronting webserver
                os.chmod(unix_socket_file, 0o660)

                return unix_sock, "unix:" + unix_socket_file

        if self.listen_address:
            return ((self.listen_address, self.listen_port),
                    _readable_listen_address(self.listen_address, self.listen_port))

        if os.name == 'nt':
            self.listen_address = '0.0.0.0'
            return ((self.listen_address, self.listen_port),
                    _readable_listen_address(self.listen_address, self.listen_port))

        address = ('::', self.listen_port)
        try:
            sock = WSGIServer.get_listener(address, family=socket.AF_INET6)
        except socket.error as ex:
            log.error('%s', ex)
            log.warning('Unable to listen on {}, trying on IPv4 only...'.format(address))
            address = ('', self.listen_port)
            sock = WSGIServer.get_listener(address, family=socket.AF_INET)

        return sock, _readable_listen_address(*address)

    @staticmethod
    def _get_args_for_reloading():
        """Determine how the script was executed, and return the args needed
        to execute it again in a new process.
        Code from https://github.com/pyload/pyload. Author GammaC0de, voulter
        """
        rv = [sys.executable]
        py_script = sys.argv[0]
        args = sys.argv[1:]
        # Need to look at main module to determine how it was executed.
        __main__ = sys.modules["__main__"]

        # The value of __package__ indicates how Python was called. It may
        # not exist if a setuptools script is installed as an egg. It may be
        # set incorrectly for entry points created with pip on Windows.
        if getattr(__main__, "__package__", "") in ["", None] or (
            os.name == "nt"
            and __main__.__package__ == ""
            and not os.path.exists(py_script)
            and os.path.exists("{}.exe".format(py_script))
        ):
            # Executed a file, like "python app.py".
            py_script = os.path.abspath(py_script)

            if os.name == "nt":
                # Windows entry points have ".exe" extension and should be
                # called directly.
                if not os.path.exists(py_script) and os.path.exists("{}.exe".format(py_script)):
                    py_script += ".exe"

                if (
                        os.path.splitext(sys.executable)[1] == ".exe"
                        and os.path.splitext(py_script)[1] == ".exe"
                ):
                    rv.pop(0)

            rv.append(py_script)
        else:
            # Executed a module, like "python -m module".
            if sys.argv[0] == "-m":
                args = sys.argv
            else:
                if os.path.isfile(py_script):
                    # Rewritten by Python from "-m script" to "/path/to/script.py".
                    py_module = __main__.__package__
                    name = os.path.splitext(os.path.basename(py_script))[0]

                    if name != "__main__":
                        py_module += ".{}".format(name)
                else:
                    # Incorrectly rewritten by pydevd debugger from "-m script" to "script".
                    py_module = py_script

                rv.extend(("-m", py_module.lstrip(".")))

        rv.extend(args)
        if os.name == 'nt':
            rv = ['"{}"'.format(a) for a in rv]
        return rv

    def _start_gevent(self):
        ssl_args = self.ssl_args or {}

        try:
            sock, output = self._make_gevent_listener()
            log.info('Starting Gevent server on %s', output)
            self.wsgiserver = WSGIServer(sock, self.app, log=self.access_logger, handler_class=MyWSGIHandler,
                                         error_log=log,
                                         spawn=Pool(), **ssl_args)
            if ssl_args:
                wrap_socket = self.wsgiserver.wrap_socket
                def my_wrap_socket(*args, **kwargs):
                    try:
                        return wrap_socket(*args, **kwargs)
                    except (ssl.SSLError, OSError) as ex:
                        log.warning('Gevent SSL Error: %s', ex)
                        raise GreenletExit

                self.wsgiserver.wrap_socket = my_wrap_socket
            self.wsgiserver.serve_forever()
        finally:
            if self.unix_socket_file:
                os.remove(self.unix_socket_file)
                self.unix_socket_file = None

    def _start_tornado(self):
        if os.name == 'nt' and sys.version_info > (3, 7):
            import asyncio
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        try:
            # Max Buffersize set to 200MB
            http_server = HTTPServer(MyWSGIContainer(self.app),
                                     max_buffer_size=209700000,
                                     ssl_options=self.ssl_args)

            unix_socket_file = os.environ.get("CALIBRE_UNIX_SOCKET")
            if os.environ.get("LISTEN_FDS") and os.name != 'nt':
                SD_LISTEN_FDS_START = 3
                sock = socket.socket(fileno=SD_LISTEN_FDS_START)
                http_server.add_socket(sock)
                sock.setblocking(0)
                socket_name =sock.getsockname()
                output = "systemd-socket:" + _readable_listen_address(socket_name[0], socket_name[1])
            elif unix_socket_file and os.name != 'nt':
                self._prepare_unix_socket(unix_socket_file)
                output = "unix:" + unix_socket_file
                unix_socket = netutil.bind_unix_socket(self.unix_socket_file)
                http_server.add_socket(unix_socket)
                # ensure current user and group have r/w permissions, no permissions for other users
                # this way the socket can be shared in a semi-secure manner
                # between the user running calibre-web and the user running the fronting webserver
                os.chmod(self.unix_socket_file, 0o660)
            else:
                output = _readable_listen_address(self.listen_address, self.listen_port)
                http_server.listen(self.listen_port, self.listen_address)
            log.info('Starting Tornado server on %s', output)

            self.wsgiserver = IOLoop.current()
            self.wsgiserver.start()
            # wait for stop signal
            self.wsgiserver.close(True)
        finally:
            if self.unix_socket_file:
                os.remove(self.unix_socket_file)
                self.unix_socket_file = None

    def start(self):
        try:
            if _GEVENT:
                # leave subprocess out to allow forking for fetchers and processors
                self._start_gevent()
            else:
                self._start_tornado()
        except Exception as ex:
            log.error("Error starting server: %s", ex)
            print("Error starting server: %s" % ex)
            self.stop()
            return False
        finally:
            self.wsgiserver = None

        # prevent irritating log of pending tasks message from asyncio
        logger.get('asyncio').setLevel(logger.logging.CRITICAL)

        if not self.restart:
            log.info("Performing shutdown of Calibre-Web")
            return True

        log.info("Performing restart of Calibre-Web")
        args = self._get_args_for_reloading()
        os.execv(args[0].lstrip('"').rstrip('"'), args)

    @staticmethod
    def shutdown_scheduler():
        from .services.background_scheduler import BackgroundScheduler
        scheduler = BackgroundScheduler()
        if scheduler:
            scheduler.scheduler.shutdown()

    def _killServer(self, __, ___):
        self.stop()

    def stop(self, restart=False):
        from . import updater_thread
        updater_thread.stop()

        log.info("webserver stop (restart=%s)", restart)
        self.shutdown_scheduler()
        self.restart = restart
        if self.wsgiserver:
            if _GEVENT:
                self.wsgiserver.close()
            else:
                if restart:
                    self.wsgiserver.call_later(1.0, self.wsgiserver.stop)
                else:
                    self.wsgiserver.asyncio_loop.call_soon_threadsafe(self.wsgiserver.stop)

