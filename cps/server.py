#!/usr/bin/env python
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

from __future__ import division, print_function, unicode_literals
import sys
import os
import signal
import socket
import logging

try:
    from gevent.pywsgi import WSGIServer
    from gevent.pool import Pool
    from gevent import __version__ as geventVersion
    gevent_present = True
except ImportError:
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop
    from tornado import version as tornadoVersion
    gevent_present = False

from . import logger, config, global_WorkerThread


class server:

    wsgiserver = None
    restart = False
    app = None
    access_logger = None

    def __init__(self):
        signal.signal(signal.SIGINT, self.killServer)
        signal.signal(signal.SIGTERM, self.killServer)

    def init_app(self, application):
        self.app = application
        self.port = config.config_port
        self.listening = config.get_config_ipaddress(readable=True) + ":" + str(self.port)
        if config.config_access_log:
            self.access_logger = logging.getLogger("access")
        else:
            self.access_logger = None

        self.ssl_args = None
        certfile_path = config.get_config_certfile()
        keyfile_path = config.get_config_keyfile()
        if certfile_path and keyfile_path:
            if os.path.isfile(certfile_path) and os.path.isfile(keyfile_path):
                self.ssl_args = {"certfile": certfile_path,
                                  "keyfile": keyfile_path}
            else:
                logger.warning('The specified paths for the ssl certificate file and/or key file seem to be broken. Ignoring ssl.')
                logger.warning('Cert path: %s', certfile_path)
                logger.warning('Key path:  %s', keyfile_path)

    def _make_gevent_socket(self):
        if config.get_config_ipaddress():
            return (config.get_config_ipaddress(), self.port)
        if os.name == 'nt':
            return ('0.0.0.0', self.port)

        try:
            s = WSGIServer.get_listener(('', self.port), family=socket.AF_INET6)
        except socket.error as ex:
            logger.error('%s', ex)
            logger.warning('Unable to listen on \'\', trying on IPv4 only...')
            s = WSGIServer.get_listener(('', self.port), family=socket.AF_INET)
        logger.debug("%r %r", s._sock, s._sock.getsockname())
        return s

    def start_gevent(self):
        ssl_args = self.ssl_args or {}
        logger.info('Starting Gevent server on %s', self.listening)

        try:
            sock = self._make_gevent_socket()
            self.wsgiserver = WSGIServer(sock, self.app, log=self.access_logger, spawn=Pool(), **ssl_args)
            self.wsgiserver.serve_forever()
        except socket.error:
            try:
                logger.info('Unable to listen on "", trying on "0.0.0.0" only...')
                self.wsgiserver = WSGIServer(('0.0.0.0', config.config_port), self.app, spawn=Pool(), **ssl_args)
                self.wsgiserver.serve_forever()
            except (OSError, socket.error) as e:
                logger.info("Error starting server: %s", e.strerror)
                print("Error starting server: %s" % e.strerror)
                global_WorkerThread.stop()
                sys.exit(1)
        except Exception:
            logger.exception("Unknown error while starting gevent")
            sys.exit(0)

    def start_tornado(self):
        logger.info('Starting Tornado server on %s', self.listening)

        try:
            # Max Buffersize set to 200MB
            http_server = HTTPServer(WSGIContainer(self.app),
                        max_buffer_size = 209700000,
                        ssl_options=self.ssl_args)
            address = config.get_config_ipaddress()
            http_server.listen(self.port, address)
            # self.access_log = logging.getLogger("tornado.access")
            self.wsgiserver=IOLoop.instance()
            self.wsgiserver.start()
            # wait for stop signal
            self.wsgiserver.close(True)
        except socket.error as err:
            logger.exception("Error starting tornado server")
            print("Error starting server: %s" % err.strerror)
            global_WorkerThread.stop()
            sys.exit(1)

    def startServer(self):
        if gevent_present:
            # leave subprocess out to allow forking for fetchers and processors
            self.start_gevent()
        else:
            self.start_tornado()

        if self.restart is True:
            logger.info("Performing restart of Calibre-Web")
            global_WorkerThread.stop()
            if os.name == 'nt':
                arguments = ["\"" + sys.executable + "\""]
                for e in sys.argv:
                    arguments.append("\"" + e + "\"")
                os.execv(sys.executable, arguments)
            else:
                os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            logger.info("Performing shutdown of Calibre-Web")
            global_WorkerThread.stop()
        sys.exit(0)

    def setRestartTyp(self,starttyp):
        self.restart = starttyp

    def killServer(self, signum, frame):
        self.stopServer()

    def stopServer(self):
        if self.wsgiserver:
            if gevent_present:
                self.wsgiserver.close()
            else:
                self.wsgiserver.add_callback(self.wsgiserver.stop)

    @staticmethod
    def getNameVersion():
        if gevent_present:
            return {'Gevent': 'v' + geventVersion}
        else:
            return {'Tornado': 'v' + tornadoVersion}
