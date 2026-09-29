=============================
Configure - Local Audio Files
=============================
This document will show you how to configure Trunk Player using nginx as a frontend reverse proxy and serving the audio files from local storage

Currently install is based on a Debian like system, Ubuntu.

System Prerequisites
====================

* After installing using `install.rst` as a guide

All paths in the document are based on trunk-player being in /home/radio, change as needed

Nginx
=====

Using your system packageing tool install the current version of Nginx

Using apt-get in unbuntu

.. code-block:: console

  $ sudo apt-get install nginx

Use the sample nginx config file in the project as a starting point

.. code-block:: console

  $ cd /home/radio/trunk-player
  $ cp trunk_player/trunk_player.nginx.sample trunk_player/trunk_player.nginx

Link this config into the nginx config area for active configs, we will also remove the default conig shipped with nginx. *Leave this if you are alreading using nginx with other sites on the same server, you will need to remove the "default" statemnets from our sample if so"*

.. code-block:: console

  $ sudo ln -s /home/radio/trunk-player/trunk_player/trunk_player.nginx /etc/nginx/sites-enabled/
  $ sudo rm /etc/nginx/sites-enabled/default

Restart nginx to pick up the new configs

.. code-block:: console

  $ sudo systemctl restart nginx 


Configure Trunk Player to use local audio files
===============================================

Edit local settings file ``trunk_player/settings_local.py``

Change

``AUDIO_URL_BASE = '//s3.amazonaws.com/SET-TO-MY-BUCKET/'``

to

``AUDIO_URL_BASE = '/audio_files/'``

If you are not running an SSL (HTTPS) site add this to the end of `trunk_player/settings_local.py`

``SECURE_PROXY_SSL_HEADER = ()``


Static html files
=================

Have django put all the static files javascript, css, and images into a static folder that ngix can server.

You need to re run this command any time any of these files is changed.

Start by starting the python virtual environment (if you have not yet)

.. code-block:: console

  $ source env/bin/activate
  $ ./manage.py collectstatic --noinput

Starting django web services
============================

Everything (web pages and the websockets used for live updates) is served by
daphne. Nginx passes requests to it on port 7055. Redis must be running.

Make sure you are in the python virtual environment, then:

.. code-block:: console

  $ daphne trunk_player.asgi:application --port 7055 --bind 127.0.0.1

To run it as a service see :doc:`supervisor`.

.. note:: Older versions of these docs also started ``./manage.py runworker``
   processes. They are no longer needed, stop them if you still run them.

Adding new transmissions
========================

You can use utility/trunk-recoder/encode-upload.sh as a guide. You want to have both the json and an mp3 file in the audio_files folder.

.. code-block:: console

  $ ./manage.py add_transmission 1200-1488505593_8.60713e+08

Note: you leave off the extenson of the filename
