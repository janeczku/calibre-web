
import os
import sys
base_path = os.path.dirname(os.path.abspath(__file__))

# Insert local directories into path
sys.path.append(os.path.join(base_path, 'lib'))

from cps import web
from cps import config
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

global title_sort

def title_sort(title):
    return title
if config.DEVELOPMENT:
    web.app.run(host="0.0.0.0",port=config.PORT, debug=True)
else:
    http_server = HTTPServer(WSGIContainer(web.app))
    http_server.listen(config.PORT)
    IOLoop.instance().start()
