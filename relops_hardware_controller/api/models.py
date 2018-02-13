# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import taskcluster


class TaskclusterUser:
    """Stubs out the is_authenticated permission and sets TC scopes.

    NB: not DB backed

    In the future we might want to make this a proper django user and
    map scopes to permissions.
    """

    def __init__(self, client_id='', scopes=[], is_authenticated=False):
        self.client_id = client_id
        self.is_authenticated = is_authenticated
        self.scopes = scopes

    def is_authenticated(self):
        return self.is_authenticated

    def has_required_scopes(self, required_scope_sets):
        # see: https://github.com/taskcluster/taskcluster-client.py#scopes
        return taskcluster.utils.scopeMatch(self.scopes, required_scope_sets)
