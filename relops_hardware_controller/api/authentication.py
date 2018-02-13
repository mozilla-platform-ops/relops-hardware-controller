import logging

from rest_framework import authentication
from rest_framework import exceptions
import taskcluster

from .models import TaskclusterUser

logger = logging.getLogger(__name__)


class TaskclusterAuthentication(authentication.BaseAuthentication):

    def authenticate(self, request):
        """A DRF authentication class.

        Takes a request and returns the tuple of (TaskClusterUser, None)
        for a successful authenticateHawk response or raises an
        AuthenticationFailed exception.

        When behind a proxy enable the djanog USE_X_FORWARDED_PORT settings should be enable to use the right port.
        https://docs.djangoproject.com/en/1.11/ref/settings/#std:setting-USE_X_FORWARDED_PORT
        """
        if request.method == 'OPTIONS':
            return None, None

        tc_client = taskcluster.Auth()

        # auth input schema:
        # http://schemas.taskcluster.net/auth/v1/authenticate-hawk-request.json
        payload = dict(
            method=request.method.lower(),
            resource=request.get_full_path(),
            host=request.get_host(),
            port=int(request.get_port()),
            authorization=request.META.get('HTTP_AUTHORIZATION', ''))

        if request.META.get('HTTP_X_FORWARDED_PROTO') == 'https':
            payload['port'] = 443

        # auth output schema: http://schemas.taskcluster.net/auth/v1/authenticate-hawk-response.json
        auth_response = tc_client.authenticateHawk(payload)

        client_id = auth_response.get('clientId', '')
        logger.debug("client_id:{}".format(client_id))

        if 'status' not in auth_response:
            raise exceptions.AuthenticationFailed('\'status\' not found invalid auth response')
        elif auth_response['status'] == 'auth-failed':
            raise exceptions.AuthenticationFailed(auth_response.get('message', 'Unknown auth failure.'))
        elif auth_response['status'] != 'auth-success':
            raise exceptions.AuthenticationFailed('invalid auth response status: %s %s'
                                                  % (auth_response['status'], auth_response.get('message', '')))

        return TaskclusterUser(client_id=client_id,
                               scopes=auth_response.get('scopes', []),
                               is_authenticated=True), None
