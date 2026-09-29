================================
Settings - List of all settings
================================

This document will list all settings used by trunk player. The settings are read from the base settings file ``trunk_player/settings.py`` and also the local file you can override ``trunk_player/settings_local.py``

These include settings from the base Django code. `Complete list from Django`_ These will be prefixed with a [D], Settings for 3rd party django apps will be prefixed with [D3]


.. _Complete list from Django: https://docs.djangoproject.com/en/1.11/topics/settings/


SITE_TITLE
==========

This value will be used for html page titles.

SECRET_KEY
==========

[D] Django secret key. Used by the system for all encoding and encrypting of values. **Very important you change this to your own random value**

DEBUG
=====

[D] When DEUG is True Djago will display debug messages for error on the web page. You do not want this set on an open site. This can expose sensitive data to users.

ALLOWED_HOSTS
=============

[D] This is a list of host names the web page can be accessed in, you need to set this domain name(s) of your site.

DATABASES
=========

[D] Configuration data for your database connection

SITE_EMAIL
==========

Email address emails will come from

DEFAULT_FROM_EMAIL
==================

Email address emails will come from

AUDIO_URL_BASE
==============

URL where your audio files are accessiable at. Defaults to ``/audio_files/``
(served by nginx, or by ``runserver`` when ``DEBUG`` is on). For S3 use
something like ``//s3.amazonaws.com/MY-BUCKET/``

CSRF_TRUSTED_ORIGINS
====================

[D] When the site is served over https, list its address here (for example
``https://scanner.example.com``) or logging in fails with a CSRF error.
Environment variable takes a space separated list.

REDIS_URL
=========

Address of the redis server used for live updates and caching, default
``redis://127.0.0.1:6379``

ADD_TRANS_AUTH_TOKEN
====================

Secret token scripts must send to ``/api_v2/import_transmission/`` to add
calls. The API is disabled until you set it.

TIME_ZONE
=========

[D] Timezone settings

`List of timezones`_ You can set to your local timezone.

.. _List of timezones: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

ACCESS_TG_RESTRICT
==================

If set to true all talkgroups are restricted and each user needs to be explicitly granted permission in the talkgroupaccess table

GOOGLE_ANALYTICS_PROPERTY_ID
============================

Google ID used for analytics


LOGIN_REDIRECT_URL
==================

[D3] Where the user is redirected after they login


.. note:: The settings below this point will most likely not need to be edited

JS_SETTINGS
===========

Used to allow the page javascript visibility into the settings in the list

JS_SETTINGS
===========

Used to allow the django HTML template engine visibility into the settings in the list

ALLOW_ANONYMOUS
===============

Not used for anything


RADIO_DEFAULT_UNIT_AGENCY
=========================

DB ID of the default acency when a new unit is added
* This is defaulted to 0 which is invalid in mysql


SOCIALACCOUNT_PROVIDERS
=======================

[D3] Config settings to allow google authentication

ACCOUNT_AUTHENTICATION_METHOD
=============================

[D3] Default username setup

ACCOUNT_EMAIL_REQUIRED
======================

[D3] Require email address

BASE_DIR
========

[D] Base directory the project is installed in.

LOGIN_URL
=========

[D] The url django will redirect users who are not looged in when a page requires login.

INSTALLED_APPS
==============

[D] List of the django apps that make up the project.

MIDDLEWARE_CLASSES
==================

[D] List of middleware code that is run in the project

ROOT_URLCONF
============

[D] Where the primary URL list comes from

TEMPLATES
=========

[D] Config values for the HTML template system

WSGI_APPLICATION
================

[D] Location of the config file for the primary web setup

AUTHENTICATION_BACKENDS
=======================

[D] How users are authenticated to django

AUTH_PASSWORD_VALIDATORS
========================

[D] How password are validated

LANGUAGE_CODE
=============

[D] Language used

USE_I18N
========

[D] Use Language code

USE_L10N
========

[D] localized formatting

USE_TZ
======

[D] Use localtime zones

SECURE_PROXY_SSL_HEADER
=======================

[D] Used to make sure HTTPS connections are set

STATIC_URL
==========

[D] URL Prefix for static content

STATIC_ROOT
===========

[D] Directory location of static files

REST_FRAMEWORK
==============

[D] Config for the REST (API) framework

MEDIA_URL
=========

[D] URL prefix for media data

MEDIA_URL
=========

[D] Directory location of media files

CHANNEL_LAYERS
==============

[D] Config of the channel app. This is where the websock data is accessed from.

CACHES
======

[D] Config of the local cache

SITE_ID
=======

[D] ID of this site

USE_RAW_ID_FIELDS
=================

[D] For very large systems, the admin page may load better with raw id fields

OPEN_SITE
=========

When true anyone can create an account at ``/accounts/signup/`` (also linked
from the login page). When false only the admin can add users.

GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
=======================================

Turns on "Sign in with Google". Create an OAuth client in the Google Cloud
console with the redirect URI ``https://<your site>/accounts/google/login/callback/``.
New accounts are only created through Google when ``OPEN_SITE`` is on.

EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
============================================================

[D] Mail server used for password reset and account emails. Without
``EMAIL_HOST`` emails are written to the log instead and email addresses are
not verified.


DUPLICATE_CALL_SECONDS
======================

When more than one recorder (source) records the same talkgroup, recordings
starting within this many seconds of each other are treated as the same call
and only one is listed: the talkgroup's *play source* if set, otherwise the
longer recording. Default ``3``, ``0`` lists every recording. Run
``./manage.py mark_duplicate_calls`` once to apply it to calls added before.
