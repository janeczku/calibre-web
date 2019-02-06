#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from cps import create_app
from cps.web import web
from cps import Server

if __name__ == '__main__':
    app = create_app()
    app.register_blueprint(web)
    Server.startServer()




