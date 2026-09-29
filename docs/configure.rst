=============
Configuration
=============
Post install configurations


Site Title/Name
===============

In ``trunk_player/settings_local.py`` set the 

.. code-block:: console

  SITE_TITLE = 'Trunk-Player'


Media Location
==============

Audio files are played from ``/audio_files/`` by default. To serve them from
amazon s3 instead, in ``trunk_player/settings_local.py`` include the base url for the s3 location of your audio files

.. code-block:: console

  AUDIO_URL_BASE = '//s3.amazonaws.com/SET-TO-MY-BUCKET/'


Set Timezone
============

In ``trunk_player/settings_local.py`` set the 

.. code-block:: console

  TIME_ZONE = 'America/Los_Angeles'
