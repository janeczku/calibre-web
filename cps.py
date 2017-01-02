#!/usr/bin/env python

import os
import sys
from threading import Thread
from multiprocessing import Queue
import time

base_path = os.path.dirname(os.path.abspath(__file__))

# Insert local directories into path
sys.path.insert(0, os.path.join(base_path, 'vendor'))

from cps import web
from cps import config
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

global title_sort


def start_calibreweb(messagequeue):
    web.global_queue = messagequeue
    if config.DEVELOPMENT:
        web.app.run(host="0.0.0.0", port=config.PORT, debug=True)
    else:
        http_server = HTTPServer(WSGIContainer(web.app))
        http_server.listen(config.PORT)
        IOLoop.instance().start()
        print "Tornado finished"
        http_server.stop()


def stop_calibreweb():
    # Close Database connections for user and data
    web.db.session.close()
    web.db.engine.dispose()
    web.ub.session.close()
    web.ub.engine.dispose()
    test=IOLoop.instance()
    test.add_callback(test.stop)
    print("Asked Tornado to exit")


if __name__ == '__main__':
    if config.DEVELOPMENT:
        web.app.run(host="0.0.0.0",port=config.PORT, debug=True)
    else:
        while True:
            q = Queue()
            t = Thread(target=start_calibreweb, args=(q,))
            t.start()
            while True: #watching queue, if there is no call than sleep, otherwise break
                if q.empty():
                    time.sleep(1)
                else:
                    break
            stop_calibreweb()
            t.join()

