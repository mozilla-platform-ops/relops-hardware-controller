
import logging

from rest_framework import authentication
from rest_framework import exceptions
import taskcluster

from .models import TaskclusterUser

logger = logging.getLogger(__name__)


class TaskclusterAuthentication(authentication.BaseAuthentication):

    tc_client = taskcluster.Auth()

    def authenticate(self, request):
        """A DRF authentication class.

        Takes a request and returns the tuple of (TaskClusterUser, None)
        for a successful authenticateHawk response or raises an
        AuthenticationFailed exception.

        When behind a proxy enable the djanog USE_X_FORWARDED_PORT settings should be enable to use the right port.
        https://docs.djangoproject.com/en/1.11/ref/settings/#std:setting-USE_X_FORWARDED_PORT
        """

        # auth input schema:
        # http://schemas.taskcluster.net/auth/v1/authenticate-hawk-request.json
        payload = dict(
            method=request.method.lower(),
            resource=request.META.get('PATH_INFO'),
            host=request.META.get('HTTP_HOST', '').split(':')[0],  # server hostname or ipv4 address
            port=int(request.get_port()),
            authorization=request.META.get('HTTP_AUTHORIZATION', ''))

        # auth output schema: http://schemas.taskcluster.net/auth/v1/authenticate-hawk-response.json
        auth_response = self.tc_client.authenticateHawk(payload)

        logger.debug('tc auth response: %s' % auth_response)

        if 'status' not in auth_response:
            raise exceptions.AuthenticationFailed('\'status\' not found invalid auth response')
        elif auth_response['status'] == 'auth-failed':
            raise exceptions.AuthenticationFailed(auth_response.get('message', 'Unknown auth failure.'))
        elif auth_response['status'] != 'auth-success':
            raise exceptions.AuthenticationFailed('invalid auth response status: %s %s'
                                                  % (auth_response['status'], auth_response.get('message', '')))

        return TaskclusterUser(scopes=auth_response.get('scopes', []),
                               is_authenticated=True), None
