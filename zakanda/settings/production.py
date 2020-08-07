# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import datetime
import urlparse
import dj_database_url

# ----------- ENVIRONMENT ------------
# essential variables are collected without the get method so if they are missing we get an Exception
django_secret_key = os.environ['DJANGO_SECRET_KEY']
xml_soccer_api_key = os.environ['XMLSOCCER_API_KEY']
sportmonks_api_key = os.environ['SPORTMONKS_API_KEY']
mailgun_api_key = os.environ['MAILGUN_API_KEY']
mailgun_password = os.environ['MAILGUN_SMTP_PASSWORD']
pg_zakanda_host = os.environ['POSTGRES_ZAKANDA_HOST']
pg_zakanda_db_password = os.environ['POSTGRES_ZAKANDA_PASSWORD']
pg_db_name = os.environ.get('ZAKANDA_DB_NAME', 'zakanda_db')
redis_url = os.environ.get('REDIS_URL')
redis_host_env = os.environ.get('REDIS_HOST')
redis_port_env = os.environ.get('REDIS_PORT', '6379')
redis_password_env = os.environ.get('REDIS_PASSWORD', '')
stream_api_key = os.environ['STREAM_API_KEY']
stream_api_secret = os.environ['STREAM_API_SECRET']
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']
admin_email = os.environ['ADMIN_EMAIL']
skrill_test_merchant = os.environ['SKRILL_TEST_MERCHANT']
skrill_test_merchant_secret_word = os.environ['SKRILL_TEST_MERCHANT_SECRET_WORD']
skrill_api_password = os.environ['SKRILL_API_PASSWORD']
# ----------- END ENVIRONMENT ------------

# ----------- ENV VALUES ASSIGNMENT ------------
SECRET_KEY = django_secret_key  # SECURITY WARNING: keep the secret key used in production secret!
XMLSOCCER_API_KEY = xml_soccer_api_key
EMAIL_HOST_PASSWORD = mailgun_password
ADMINS = [('admin', admin_email)]
MANAGERS = ADMINS
STREAM_API_KEY = stream_api_key  # used by stream-django app
STREAM_API_SECRET = stream_api_secret  # used by stream-django app
SKRILL_PAY_TO_EMAIL = skrill_test_merchant
SKRILL_SECRET_WORD = skrill_test_merchant_secret_word
SKRILL_API_PASSWORD = skrill_api_password
redis_host, redis_port, redis_password = '', '', ''
if redis_url:
    redis_url_parsed = urlparse.urlparse(redis_url)  # REDIS_URL=redis://192.168.50.1:6379 (heroku uses this format)
    redis_host = redis_url_parsed.hostname
    redis_port = redis_url_parsed.port
    redis_password = redis_url_parsed.password
if redis_host_env:
    # if host, port and password are explicitly defined by individual variables they override REDIS_URL env variable
    redis_host = redis_host_env
    redis_port = redis_port_env
    redis_password = redis_password_env
# ----------- END ENV VALUES ASSIGNMENT ------------

DEBUG = False
ALLOWED_HOSTS = [
    'www.zakanda.com', 'zakanda.com', 'zakanda.herokuapp.com', '192.168.99.101',
    # aws container instances public IPS
    '3.122.97.158', '3.120.158.25',
    # 'zakanda-alb-578568019.eu-central-1.elb.amazonaws.com',
    # aws container instances private IPS used by load balancer health checks
    '172.31.21.25', '172.31.3.10'
]
SECURE_SSL_REDIRECT = False  # redirection to https is done by the load balancer
# If you put the django app behind a proxy like NginX you must configure the following setting
# This tells Django to trust the X-Forwarded-Proto header that comes from our proxy, and any time its value is 'https',
# then the request is guaranteed to be secure (i.e., it originally came in via HTTPS).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

logfile_dir = os.path.dirname(os.path.abspath(__file__))
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s pr:%(process)d thr:%(thread)d] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'to_console': {
            'format': " >>> [%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': ' >>> [%(name)s:%(lineno)s] %(message)s'
        },
        "rq_console": {
            "format": "%(asctime)s %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': logfile_dir+'/logfile.log',
            'formatter': 'verbose'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'to_console'
        },
        "rq_console": {
            "level": "DEBUG",
            "class": "rq.utils.ColorizingStreamHandler",
            "formatter": "rq_console",
            "exclude": ["%(asctime)s"],
        },

    },
    'loggers': {
        # This logger logs the default django log messages
        'django': {
            'handlers': ['file', 'console'],
            'propagate': True,
            'level': 'INFO',
        },
        "rq.worker": {
            "handlers": ['file', "rq_console"],
            "level": "INFO"
        },
        'zakanda': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'xmlSoccerParser': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'games': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'bet_slip': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'user_accounts': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'bet_statistics': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'feeds': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'gutils': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'bet_tagging': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'avatar_extension': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'emails': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'register_history': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'data_sources': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'sportmonks': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'skrill': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
                },
        'wallet': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
                },
        # 'django.db': {
        #     'handlers': ['file', 'console'],
        #     'level': 'DEBUG',
        # }
    }
}
# INSTALLED_APPS += (
#     'prod_only app'
# )

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': pg_db_name,
        'HOST': pg_zakanda_host,
        'PORT': '5432',
        'USER': 'postgres',
        'PASSWORD': pg_zakanda_db_password
    }
}
# Reads db from DATABASE_URL env variable. if variable doesn't exist doesn't affect the Databases dictionary
# DATABASE_URL format: postgres://USER:PASSWORD@HOST:PORT/NAME
db_from_env = dj_database_url.config()
DATABASES['default'].update(db_from_env)

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': [
            "{0}:{1}".format(redis_host, redis_port),
        ],
        'KEY_PREFIX': '',
        'OPTIONS': {
            'DB': 0,
            'PASSWORD': redis_password,
        },
    }
}

RQ_QUEUES = {
    'default': {
        'HOST': redis_host,
        'PORT': redis_port,
        'DB': 0,
        'PASSWORD': redis_password,
        # 'DEFAULT_TIMEOUT': 360,
    },
    'high': {
        'HOST': redis_host,
        'PORT': redis_port,
        'DB': 0,
        'PASSWORD': redis_password,
        # 'DEFAULT_TIMEOUT': 360,
    },
    'low': {
        'HOST': redis_host,
        'PORT': redis_port,
        'DB': 0,
        'PASSWORD': redis_password,
        # 'DEFAULT_TIMEOUT': 360,
    },
    'emails': {
        'HOST': redis_host,
        'PORT': redis_port,
        'DB': 0,
        'PASSWORD': redis_password,
        # 'DEFAULT_TIMEOUT': 360,
    }
}

AWS_FILE_EXPIRE = 200
AWS_PRELOAD_METADATA = True  # so that only updated files are saved in s3 when collectstatic is called?
AWS_QUERYSTRING_AUTH = True
# AWS_S3_FILE_OVERWRITE = True
DEFAULT_FILE_STORAGE = 'zakanda.utils.MediaRootS3Boto3Storage'  # user uploaded files
STATICFILES_STORAGE = 'zakanda.utils.StaticRootS3Boto3Storage'  # collectstatic will send files here
S3DIRECT_REGION = 'eu-central-1'
AWS_S3_REGION_NAME = 'eu-central-1'
AWS_S3_SIGNATURE_VERSION = 's3v4'
S3_URL = '//%s.s3.amazonaws.com/' % AWS_STORAGE_BUCKET_NAME
MEDIA_URL = S3_URL + 'media/'
MEDIA_ROOT = MEDIA_URL
STATIC_URL = S3_URL + 'static/'
# STATIC_ROOT = STATIC_URL
ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'
two_months = datetime.timedelta(days=61)
date_two_months_later = datetime.date.today() + two_months
expires = date_two_months_later.strftime("%A, %d %B %Y 20:00:00 GMT")
AWS_HEADERS = {
    'Expires': expires,
    'Cache-Control': 'max-age=%d' % (int(two_months.total_seconds()), ),
}

# Disable new users signup
# look at user_accounts/adapter.py
ACCOUNT_ADAPTER = 'user_accounts.adapter.NoNewUsersAccountAdapter'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
