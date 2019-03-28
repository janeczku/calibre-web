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


import sys
import os
import signal
from socket import error as SocketError

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

from cps import web

from cps import logger
log = logger.create()


class server:
    wsgiserver = None
    restart = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.killServer)
        signal.signal(signal.SIGTERM, self.killServer)

        ssl_args = None
        certfile_path   = web.ub.config.get_config_certfile()
        keyfile_path    = web.ub.config.get_config_keyfile()
        if certfile_path and keyfile_path:
            if os.path.isfile(certfile_path) and os.path.isfile(keyfile_path):
                ssl_args = {"certfile": certfile_path,
                            "keyfile": keyfile_path}
            else:
                log.warning('The specified paths for the ssl certificate file and/or key file seem to be broken. Ignoring ssl.')
                log.warning('Cert path: %s', certfile_path)
                log.warning('Key path:  %s', keyfile_path)
        self.ssl_args = ssl_args

    def start_gevent(self):
        ssl_args = self.ssl_args or dict()
        try:
            if os.name == 'nt':
                self.wsgiserver= WSGIServer(('0.0.0.0', web.ub.config.config_port), web.app, spawn=Pool(), **ssl_args)
            else:
                self.wsgiserver = WSGIServer(('', web.ub.config.config_port), web.app, spawn=Pool(), **ssl_args)
            web.py3_gevent_link = self.wsgiserver
            self.wsgiserver.serve_forever()

        except SocketError:
            try:
                log.info('Unable to listen on \'\', trying on IPv4 only...')
                self.wsgiserver = WSGIServer(('0.0.0.0', web.ub.config.config_port), web.app, spawn=Pool(), **ssl_args)
                web.py3_gevent_link = self.wsgiserver
                self.wsgiserver.serve_forever()
            except (OSError, SocketError) as ex:
                log.info('Error starting server: %s', ex)
                print("Error starting server: %s" % ex)
                web.helper.global_WorkerThread.stop()
                sys.exit(1)
        except Exception:
            log.info('Unknown error while starting gevent')

    def startServer(self):
        if gevent_present:
            log.info('Starting Gevent server')
            # leave subprocess out to allow forking for fetchers and processors
            self.start_gevent()
        else:
            try:
                log.info('Starting Tornado server')

                # Max Buffersize set to 200MB
                http_server = HTTPServer(WSGIContainer(web.app),
                            max_buffer_size = 209700000,
                            ssl_options=self.ssl_args)
                http_server.listen(web.ub.config.config_port)
                self.wsgiserver=IOLoop.instance()
                self.wsgiserver.start()
                # wait for stop signal
                self.wsgiserver.close(True)
            except SocketError as ex:
                log.info('Error starting server: %s', ex)
                print("Error starting server: %s" % ex)
                web.helper.global_WorkerThread.stop()
                sys.exit(1)

        # ToDo: Somehow caused by circular import under python3 refactor
        if sys.version_info > (3, 0):
            self.restart = web.py3_restart_Typ
        if self.restart == True:
            log.info('Performing restart of Calibre-Web')
            web.helper.global_WorkerThread.stop()
            if os.name == 'nt':
                arguments = ["\"" + sys.executable + "\""]
                for e in sys.argv:
                    arguments.append("\"" + e + "\"")
                os.execv(sys.executable, arguments)
            else:
                os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            log.info('Performing shutdown of Calibre-Web')
            web.helper.global_WorkerThread.stop()
        sys.exit(0)

    def setRestartTyp(self,starttyp):
        self.restart = starttyp
        # ToDo: Somehow caused by circular import under python3 refactor
        web.py3_restart_Typ = starttyp

    def killServer(self, signum, frame):
        self.stopServer()

    def stopServer(self):
        # ToDo: Somehow caused by circular import under python3 refactor
        if sys.version_info > (3, 0):
            if not self.wsgiserver:
                if gevent_present:
                    self.wsgiserver = web.py3_gevent_link
                else:
                    self.wsgiserver = IOLoop.instance()
        if self.wsgiserver:
            if gevent_present:
                self.wsgiserver.close()
            else:
                self.wsgiserver.add_callback(self.wsgiserver.stop)

    @staticmethod
    def getNameVersion():
        if gevent_present:
            return {'Gevent':'v'+geventVersion}
        else:
            return {'Tornado':'v'+tornadoVersion}


# Start Instance of Server
Server=server()
