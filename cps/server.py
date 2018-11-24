#!/usr/bin/env python
# -*- coding: utf-8 -*-

from socket import error as SocketError
import sys
import os
import signal
import web

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


class server:

    wsgiserver = None
    restart= False

    def __init__(self):
        signal.signal(signal.SIGINT, self.killServer)
        signal.signal(signal.SIGTERM, self.killServer)

    def start_gevent(self):
        try:
            ssl_args = dict()
            certfile_path   = web.ub.config.get_config_certfile()
            keyfile_path    = web.ub.config.get_config_keyfile()
            if certfile_path and keyfile_path:
                if os.path.isfile(certfile_path) and os.path.isfile(keyfile_path):
                    ssl_args = {"certfile": certfile_path,
                                "keyfile": keyfile_path}
                else:
                    web.app.logger.info('The specified paths for the ssl certificate file and/or key file seem to be broken. Ignoring ssl. Cert path: %s | Key path: %s' % (certfile_path, keyfile_path))
            if os.name == 'nt':
                self.wsgiserver= WSGIServer(('0.0.0.0', web.ub.config.config_port), web.app, spawn=Pool(), **ssl_args)
            else:
                self.wsgiserver = WSGIServer(('', web.ub.config.config_port), web.app, spawn=Pool(), **ssl_args)
            self.wsgiserver.serve_forever()
        except SocketError:
            try:
                web.app.logger.info('Unable to listen on \'\', trying on IPv4 only...')
                self.wsgiserver = WSGIServer(('0.0.0.0', web.ub.config.config_port), web.app, spawn=Pool(), **ssl_args)
                self.wsgiserver.serve_forever()
            except (OSError, SocketError) as e:
                web.app.logger.info("Error starting server: %s" % e.strerror)
                print("Error starting server: %s" % e.strerror)
                web.helper.global_WorkerThread.stop()
                sys.exit(1)
        except Exception:
            web.app.logger.info("Unknown error while starting gevent")

    def startServer(self):
        if gevent_present:
            web.app.logger.info('Starting Gevent server')
            # leave subprocess out to allow forking for fetchers and processors
            self.start_gevent()
        else:
            try:
                ssl = None
                web.app.logger.info('Starting Tornado server')
                certfile_path   = web.ub.config.get_config_certfile()
                keyfile_path    = web.ub.config.get_config_keyfile()
                if certfile_path and keyfile_path:
                    if os.path.isfile(certfile_path) and os.path.isfile(keyfile_path):
                        ssl = {"certfile": certfile_path,
                               "keyfile": keyfile_path}
                    else:
                        web.app.logger.info('The specified paths for the ssl certificate file and/or key file seem to be broken. Ignoring ssl. Cert path: %s | Key path: %s' % (certfile_path, keyfile_path))

                # Max Buffersize set to 200MB
                http_server = HTTPServer(WSGIContainer(web.app),
                            max_buffer_size = 209700000,
                            ssl_options=ssl)
                http_server.listen(web.ub.config.config_port)
                self.wsgiserver=IOLoop.instance()
                self.wsgiserver.start()
                # wait for stop signal
                self.wsgiserver.close(True)
            except SocketError as e:
                web.app.logger.info("Error starting server: %s" % e.strerror)
                print("Error starting server: %s" % e.strerror)
                web.helper.global_WorkerThread.stop()
                sys.exit(1)

        if self.restart == True:
            web.app.logger.info("Performing restart of Calibre-Web")
            web.helper.global_WorkerThread.stop()
            if os.name == 'nt':
                arguments = ["\"" + sys.executable + "\""]
                for e in sys.argv:
                    arguments.append("\"" + e + "\"")
                os.execv(sys.executable, arguments)
            else:
                os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            web.app.logger.info("Performing shutdown of Calibre-Web")
            web.helper.global_WorkerThread.stop()
        sys.exit(0)

    def setRestartTyp(self,starttyp):
        self.restart=starttyp

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
            return {'Gevent':'v'+geventVersion}
        else:
            return {'Tornado':'v'+tornadoVersion}


# Start Instance of Server
Server=server()
