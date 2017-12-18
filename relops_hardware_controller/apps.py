# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from django_redis import get_redis_connection

from django.conf import settings
from django.apps import AppConfig


logger = logging.getLogger('django')


class RelopsHardwareControllerAppConfig(AppConfig):
    name = 'relops_hardware_controller'

    def ready(self):
        # The app is now ready.

        # For some unknown reason, if you don't do at least one read
        # from the Redis connection before you do your first write,
        # you can get a `redis.exceptions.ConnectionError` with
        # "Error 9 while writing to socket. Bad file descriptor."
        # This is only occuring in running unit tests.
        # But only do this if the caches['default'] isn't a fake one
        # redis_client_class = settings.CACHES['default']['OPTIONS'].get(
        #     'REDIS_CLIENT_CLASS'
        # )
        # if redis_client_class != 'fakeredis.FakeStrictRedis':
        if 'LocMemCache' not in settings.CACHES['default']['BACKEND']:
            connection = get_redis_connection('default')
            connection.info()
