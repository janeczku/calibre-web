# -*- coding: utf-8 -*-

#  Flask License
#
#  Copyright © 2010 by the Pallets team, cervinko, janeczku, OzzieIsaacs
#
#  Some rights reserved.
#
#  Redistribution and use in source and binary forms of the software as
#  well as documentation, with or without modification, are permitted
#  provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice,
#  this list of conditions and the following disclaimer.
#
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
#  * Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#  THIS SOFTWARE AND DOCUMENTATION IS PROVIDED BY THE COPYRIGHT HOLDERS AND
#  CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
#  BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#  FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
#  COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
#  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
#  USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#  ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
#  THIS SOFTWARE AND DOCUMENTATION, EVEN IF ADVISED OF THE POSSIBILITY OF
#  SUCH DAMAGE.
#
# Inspired by http://flask.pocoo.org/snippets/35/

import os

class ReverseProxied(object):
    """Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different from what is used locally.

    Code courtesy of: https://flask.pocoo.org/snippets/35/

    In nginx:
    location /myprefix {
        proxy_pass http://127.0.0.1:8083;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    If you cannot configure these headers (for instance, if you are serving calibre-web from
    behind an opaque TLS terminator or unconfigurable reverse proxy such as tailscale funnel), 
    then you may also use optional environment variables to achieve the same result. 

    To configure a prefix override (script name), set PROXY_SCRIPT_NAME
    To configure a scheme override, set PROXY_SCHEME
    To configure a host override, set PROXY_HOST
    To configure a port override, set PROXY_PORT
    """

    def __init__(self, application,
                 script_name=None, scheme=None, forwarded_host=None, port=None):
        self.app = application
        self.proxied = False

        self.env_script = script_name or os.getenv('PROXY_SCRIPT_NAME', '')
        self.env_scheme = scheme      or os.getenv('PROXY_SCHEME', '')
        self.env_host   = forwarded_host or os.getenv('PROXY_HOST', '')
        self.env_port = port or os.getenv('PROXY_PORT','')

    def __call__(self, environ, start_response):
        self.proxied = False

        script_name = environ.get('HTTP_X_SCRIPT_NAME', self.env_script)
        if script_name:
            self.proxied = True
            environ['SCRIPT_NAME'] = script_name
            path = environ.get('PATH_INFO', '')
            if path.startswith(script_name):
                environ['PATH_INFO'] = path[len(script_name):]

        scheme = (
            environ.get('HTTP_X_SCHEME', '') or
            environ.get('HTTP_X_FORWARDED_PROTO', '')
        ) or self.env_scheme
        if scheme:
            self.proxied = True
            environ['wsgi.url_scheme'] = scheme

        host = environ.get('HTTP_X_FORWARDED_HOST', self.env_host)
        if host:
            self.proxied = True
            if self.env_port and ':' not in host:
                host = f"{host}:{self.env_port}"
            environ['HTTP_HOST'] = host

        return self.app(environ, start_response)

    @property
    def is_proxied(self):
        return self.proxied