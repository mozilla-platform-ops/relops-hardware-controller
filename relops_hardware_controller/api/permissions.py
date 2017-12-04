
import logging

from rest_framework import permissions


logger = logging.getLogger(__name__)


class HasTaskclusterScopes(permissions.BasePermission):

    def has_permission(self, request, view):
        """
        Takes a successful authenticateHawk response

        Returns True if the request should be granted access, and False otherwise.
        """
        required_scope_sets = getattr(view, 'required_taskcluster_scope_sets')
        allowed = request.user.has_required_scopes(required_scope_sets)
        logger.debug('Checking provided scopes %s against required sets %s result %s' %
                     (request.user.scopes, required_scope_sets, allowed))
        return allowed
