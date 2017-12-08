# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

from django import http

from relops_hardware_controller.api import decorators


def test_set_cors_headers(rf):

    # Happy patch
    @decorators.set_cors_headers(origin='*')
    def view_function(request):
        return http.HttpResponse('hello world')

    request = rf.get('/')
    response = view_function(request)
    assert response['Access-Control-Allow-Origin'] == '*'
    assert response['Access-Control-Allow-Methods'] == 'GET'

    # Overrides
    @decorators.set_cors_headers(origin='example.com', methods=['HEAD', 'GET'])
    def view_function(request):
        return http.HttpResponse('hello world')
    response = view_function(request)
    assert response['Access-Control-Allow-Origin'] == 'example.com'
    assert response['Access-Control-Allow-Methods'] == 'HEAD,GET'
