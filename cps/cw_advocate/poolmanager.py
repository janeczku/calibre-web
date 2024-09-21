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

import collections
import functools

from urllib3 import PoolManager
from urllib3.poolmanager import _default_key_normalizer, PoolKey

from .connectionpool import (
    ValidatingHTTPSConnectionPool,
    ValidatingHTTPConnectionPool,
)

pool_classes_by_scheme = {
    "http": ValidatingHTTPConnectionPool,
    "https": ValidatingHTTPSConnectionPool,
}

AdvocatePoolKey = collections.namedtuple('AdvocatePoolKey',
                                         PoolKey._fields + ('key_validator',))


def key_normalizer(key_class, request_context):
    request_context = request_context.copy()
    # TODO: add ability to serialize validator rules to dict,
    # allowing pool to be shared between sessions with the same
    # rules.
    request_context["validator"] = id(request_context["validator"])
    return _default_key_normalizer(key_class, request_context)


key_fn_by_scheme = {
    'http': functools.partial(key_normalizer, AdvocatePoolKey),
    'https': functools.partial(key_normalizer, AdvocatePoolKey),
}


class ValidatingPoolManager(PoolManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make sure the API hasn't changed
        assert (hasattr(self, 'pool_classes_by_scheme'))

        self.pool_classes_by_scheme = pool_classes_by_scheme
        self.key_fn_by_scheme = key_fn_by_scheme.copy()
