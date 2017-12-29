

import re

from django.core.validators import (
    validate_ipv46_address,
)


hostname_re = r'^[-_\.a-z0-9](?:[-_\.a-z0-9-]{0,61}[-_\.a-z0-9])?$'


def validate_host(host):
    # from the django URLValidator without unicode
    if not re.match(hostname_re, host):
        validate_ipv46_address(host)
