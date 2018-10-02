"""
Django settings for relops_hardware_controller project.

Generated by 'django-admin startproject' using Django 1.10.4.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os
import logging
import json

from configurations import Configuration, values


class JSONFileValue(values.CastingMixin, values.Value):
    caster = 'relops_hardware_controller.settings.load_json_file'

def load_json_file(path):
    return json.load(open(path, 'r'))


class Celery:
    "Celery config settings"

    REDIS_URL = values.Value('redis://redis:6379/0', environ_prefix=None)

    # Use redis as the Celery broker.
    @property
    def CELERY_BROKER_URL(self):
        return self.REDIS_URL

    # The django_celery_results backend.
    CELERY_RESULT_BACKEND = 'django-cache'

    # Throw away task results after 1 hour, for debugging purposes.
    # CELERY_RESULT_EXPIRES = datetime.timedelta(minutes=60)

    # Track if a task has been started, not only pending etc.
    CELERY_TASK_TRACK_STARTED = True

    CELERY_TASK_SOFT_TIME_LIMIT = values.Value(60 * 10, environ_prefix=None)
    CELERY_TASK_TIME_LIMIT = values.Value(60 * 20, environ_prefix=None)


class Base(Configuration, Celery):
    # Web Settings

    SECRET_KEY = values.SecretValue()

    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = 'ugrryo)w9y0(*i^-zjq+%)=o^g*-0l%l*7!5qzrg3j$y3mtp*$'

    # Password validation
    # https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

    @property
    def CACHES(self):
        return {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': self.REDIS_URL,
                'OPTIONS': {
                    'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',  # noqa
                    'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',  # noqa
                },
            },
        }

    AUTH_PASSWORD_VALIDATORS = [
        {
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        },
    ]

    # Build paths inside the project like this: os.path.join(BASE_DIR, ...)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Internationalization
    # https://docs.djangoproject.com/en/1.10/topics/i18n/

    LANGUAGE_CODE = 'en-us'

    TIME_ZONE = values.Value('UTC', environ_prefix=None)

    USE_I18N = True

    USE_L10N = True

    USE_TZ = True

    # Static files (CSS, JavaScript, Images)
    # https://docs.djangoproject.com/en/1.10/howto/static-files/
    STATIC_URL = '/static/'

    CONN_MAX_AGE = values.IntegerValue(60, environ_prefix=None)

    ALLOWED_HOSTS = values.ListValue([], environ_prefix=None)

    CORS_ORIGIN = values.Value(environ_prefix=None)

    USE_X_FORWARDED_HOST = values.BooleanValue(False, environ_prefix=None)

    # Application definition
    INSTALLED_APPS = [
        'relops_hardware_controller.apps.RelopsHardwareControllerAppConfig',
        'relops_hardware_controller.api',

        'django_celery_results',
        'rest_framework',
    ]

    MIDDLEWARE = [
        'django.middleware.security.SecurityMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ]

    ROOT_URLCONF = 'relops_hardware_controller.urls'

    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        },
    ]

    WSGI_APPLICATION = 'relops_hardware_controller.wsgi.application'

    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'

    REST_FRAMEWORK = {
        'DEFAULT_AUTHENTICATION_CLASSES': (
        ),
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.JSONRenderer',
        ),
        'UNAUTHENTICATED_USER': 'relops_hardware_controller.api.models.TaskclusterUser',
    }

    TASKCLUSTER_CLIENT_ID = values.Value(environ_prefix=None)
    TASKCLUSTER_ACCESS_TOKEN = values.SecretValue(environ_prefix=None)

    TASK_NAMES = values.ListValue([
        'ping',
        'status',
        'reboot',
        'ipmi_off',
        'ipmi_on',
        'ipmi_list',
        'ipmi_cycle',
        'ipmi_reset',
        'reimage',
        'loan',
        'return_loan',
    ], environ_prefix=None)

    REQUIRED_TASKCLUSTER_SCOPE_SETS = values.SingleNestedListValue([
        ['project:releng:roller:{}'.format(task_name)]
        for task_name in TASK_NAMES.value
    ], seq_separator=',', environ_prefix=None)

    VALID_WORKER_ID_REGEX = values.Value('^.*', environ_prefix=None)

    # Worker Settings

    NOTIFY_EMAIL = values.Value('dhouse@mozilla.com', environ_prefix=None)
    NOTIFY_IRC_CHANNEL = values.Value('#roller', environ_prefix=None)

    BUGZILLA_URL = values.URLValue('https://bugzilla.mozilla.org', environ_prefix=None)
    BUGZILLA_API_KEY = values.SecretValue(environ_prefix=None)
    BUGZILLA_REOPEN_STATE = values.Value('REOPENED', environ_prefix=None)
    BUGZILLA_REBOOT_TEMPLATE = values.Value(json.dumps(dict(
        api_key='${api_key}',
        product='Infrastructure & Operations',
        component='DCOps',
        cc='${cc}',
        summary='${hostname} is unreachable',
        version='unspecified',
        description='Reboot ${hostname} ${ip}\nRequested by ${client_id}\nRelops controller action failed:${log}',
        blocks='${blocks}',
    )), environ_prefix=None)

    BUGZILLA_WORKER_TRACKER_TEMPLATE = values.Value(json.dumps(dict(
        api_key='${api_key}',
        product='Infrastructure & Operations',
        component='CIDuty',
        summary='${hostname} problem tracking',
        version='unspecified',
        alias='${alias}',
    )), environ_prefix=None)

    XEN_URL = values.URLValue('', environ_prefix=None)
    XEN_USERNAME = values.Value('', environ_prefix=None)
    XEN_PASSWORD = values.Value('', environ_prefix=None)

    ILO_USERNAME = values.Value('', environ_prefix=None)
    ILO_PASSWORD = values.Value('', environ_prefix=None)

    WORKER_CONFIG = JSONFileValue('', environ_prefix=None, environ_name='WORKER_CONFIG_PATH')

    # how many seconds to wait for a machine to go down and come back up
    DOWN_TIMEOUT = values.IntegerValue(60, environ_prefix=None)
    UP_TIMEOUT = values.IntegerValue(300, environ_prefix=None)

    REBOOT_METHODS = values.ListValue([
        'ssh_reboot',
        'ipmi_reset',
        'ipmi_cycle',
        'snmp_reboot',  # snmp pdu for mac minis
        'file_bugzilla_bug',  # give up and file a bug
    ], environ_prefix=None)


class Dev(Base):
    DEBUG = values.BooleanValue(True, environ_prefix=None)
    ALLOWED_HOSTS = values.ListValue(['tools.taskcluster.net', 'localhost', '127.0.0.1'], environ_prefix=None)
    CORS_ORIGIN = values.Value('*', environ_prefix=None)

    BUGZILLA_URL = values.Value('https://landfill.bugzilla.org/bugzilla-5.0-branch/rest/', environ_prefix=None)


class Prod(Base):
    ALLOWED_HOSTS = values.ListValue(['tools.taskcluster.net'], environ_prefix=None)
    CORS_ORIGIN = values.Value('tools.taskcluster.net', environ_prefix=None)


class Test(Base):
    DEBUG = False

    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
    CORS_ORIGIN = 'localhost'

    SECRET_KEY = values.Value('not-so-secret-after-all')

    BUGZILLA_URL = 'https://landfill.bugzilla.org/bugzilla-5.0-branch/rest/'
    BUGZILLA_API_KEY = values.Value('anything')

    XEN_URL = 'https://xenapiserver/'
    XEN_USERNAME = 'xen_dev_username'
    XEN_PASSWORD = values.Value('anything_zen_password')

    ILO_USERNAME = 'ilo_dev_username'
    ILO_PASSWORD = values.Value('anything_ilo_password')

    TASKCLUSTER_CLIENT_ID = 'test-tc-client-id'
    TASKCLUSTER_ACCESS_TOKEN = values.Value('test-tc-access-token')

    TASK_NAMES = [
        'ping',
    ]

    REQUIRED_TASKCLUSTER_SCOPE_SETS = [
        ['project:relops-hardware-controller:{}'.format(task_name)]
        for task_name in TASK_NAMES
    ]
