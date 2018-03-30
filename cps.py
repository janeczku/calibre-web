#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

base_path = os.path.dirname(os.path.abspath(__file__))
# Insert local directories into path
sys.path.append(base_path)
sys.path.append(os.path.join(base_path, 'cps'))
sys.path.append(os.path.join(base_path, 'vendor'))

from cps import web
try:
    from gevent.wsgi import WSGIServer
    gevent_present = True
except ImportError:
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop
    gevent_present = False

if __name__ == '__main__':
    if web.ub.DEVELOPMENT:
        web.app.run(port=web.ub.config.config_port, debug=True)
    else:
        if gevent_present:
            web.app.logger.info('Attempting to start gevent')
            web.start_gevent()
        else:
            web.app.logger.info('Falling back to Tornado')
            # Max Buffersize set to 200MB
            if web.ub.config.get_config_certfile() and web.ub.config.get_config_keyfile():
                ssl={"certfile": web.ub.config.get_config_certfile(),
                     "keyfile": web.ub.config.get_config_keyfile()}
            else:
                ssl=None
            http_server = HTTPServer(WSGIContainer(web.app),
                            max_buffer_size = 209700000,
                            ssl_options=ssl)
            http_server.listen(web.ub.config.config_port)
            IOLoop.instance().start()
            IOLoop.instance().close(True)


    if web.helper.global_task == 0:
        web.app.logger.info("Performing restart of Calibre-web")
        os.execl(sys.executable, sys.executable, *sys.argv)
    else:
        web.app.logger.info("Performing shutdown of Calibre-web")
    sys.exit(0)
