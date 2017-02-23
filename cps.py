#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

base_path = os.path.dirname(os.path.abspath(__file__))
# Insert local directories into path
sys.path.insert(0, os.path.join(base_path, 'vendor'))

from cps import web
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

if __name__ == '__main__':
    if web.ub.DEVELOPMENT:
        web.app.run(host="0.0.0.0", port=web.ub.config.config_port, debug=True)
    else:
        http_server = HTTPServer(WSGIContainer(web.app))
        http_server.listen(web.ub.config.config_port)
        IOLoop.instance().start()

    if web.helper.global_task == 0:
        web.app.logger.info("Performing restart of Calibre-web")
        os.execl(sys.executable, sys.executable, *sys.argv)
    else:
        web.app.logger.info("Performing shutdown of Calibre-web")
    sys.exit(0)
