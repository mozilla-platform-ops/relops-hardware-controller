# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import url

from . import views


urlpatterns = [
    # TODO: check TC supports registering options as query params
    # GET /jobs/${job_id}/
    url(r'^jobs$', views.JobList.as_view(), name='JobList'),
    url(r'^jobs/(?P<pk>[0-9a-f]{8}\-[0-9a-f]{4}\-4[0-9a-f]{3}\-[89ab][0-9a-f]{3}\-[0-9a-f]{12})$', views.JobDetail.as_view(), name='JobDetail'),
]
