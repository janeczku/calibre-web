#
# Copyright 2015 Jordan Milne
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Source: https://github.com/JordanMilne/Advocate

from requests.adapters import HTTPAdapter, DEFAULT_POOLBLOCK

from .addrvalidator import AddrValidator
from .exceptions import ProxyDisabledException
from .poolmanager import ValidatingPoolManager


class ValidatingHTTPAdapter(HTTPAdapter):
    __attrs__ = HTTPAdapter.__attrs__ + ['_validator']

    def __init__(self, *args, **kwargs):
        self._validator = kwargs.pop('validator', None)
        if not self._validator:
            self._validator = AddrValidator()
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, connections, maxsize, block=DEFAULT_POOLBLOCK,
                         **pool_kwargs):
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block
        self.poolmanager = ValidatingPoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            validator=self._validator,
            **pool_kwargs
        )

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        raise ProxyDisabledException("Proxies cannot be used with Advocate")
