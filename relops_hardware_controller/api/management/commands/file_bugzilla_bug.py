
import logging
import re

from django.core.management.base import BaseCommand
from django.core.validators import validate_ipv46_address
import requests

from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Files a new bugzilla bug for the host. Raises for exceptions for bad or invalid responses.'
    doc_url = 'https://github.com/mozbhearsum/bzrest/blob/master/bzrest/client.py'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument(
            'host',
            type=str,
            help='A host',
        )

    def get_args_and_kwargs_from_job(self, _, machine):
        args = [machine.get('host', None) or machine.get('ip', None)]
        kwargs = {}
        return args, kwargs

    def validate_host(self, host):
        # from the django URLValidator without unicode
        hostname_re = r'^[\.a-z0-9](?:[\.a-z0-9-]{0,61}[\.a-z0-9])?$'
        if not re.match(hostname_re, host):
            validate_ipv46_address(host)

    def handle(self, host, *args, **options):
        self.validate_host(host)

        bgz_url = settings.BUGZILLA_URL
        if bgz_url.endswith('/'):
            url = bgz_url + 'bug'
        else:
            url = bgz_url + '/bug'

        response = requests.post(
            url,
            json=dict(
                Bugzilla_api_key=settings.BUGZILLA_API_KEY,
                product='Infrastructure & Operations',
                component='DCOps',
                summary='{} is unreachable'.format(host),
                version='other',
                op_sys='All',
                platform='All',
                # blocks=  # TODO: add machine bug id for tracking
            ),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        logger.debug('file bug response: {}'.format(response.content))
        response.raise_for_status()
        # will raise errors from invalid JSON too
        bug_id = response.json()["id"]
        logger.info('created bug {} for {}'.format(bug_id, host))
