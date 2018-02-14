# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import url

from . import views

app_name = 'api'
urlpatterns = [
    url(r'^workers/(?P<worker_id>[-_0-9a-zA-Z]{1,128})/'
        'jobs$',
        views.queue_job, name='JobList'),
]
