import os
import sys
import time

base_path = os.path.dirname(os.path.abspath(__file__))

# Insert local directories into path
sys.path.insert(0, os.path.join(base_path, 'vendor'))

from cps import web
# from cps import config
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

if __name__ == '__main__':
    '''if config.DEVELOPMENT:
        web.app.run(host="0.0.0.0", port=web.config.config_port, debug=True)
    else:'''
    http_server = HTTPServer(WSGIContainer(web.app))
    http_server.listen(web.config.config_port)
    IOLoop.instance().start()

    if web.global_task == 0:
        print("Performing restart of Calibre-web")
        os.execl(sys.executable,sys.executable, *sys.argv)
    else:
        print("Performing shutdown of Calibre-web")
    os._exit(0)
