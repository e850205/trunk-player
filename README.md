Trunk Player
============

A web site for listening to radio calls recorded by [trunk-recorder](https://github.com/robotastic/trunk-recorder).
Calls show up in your browser as they are recorded, and you can play them live like a scanner or go back through the history.

![Main Screen](docs/images/trunk_player_main.png?raw=true "Main Screen")

* **Live scanner.** Press *Start Scanner* and new calls play as they come in, with no page reloads.
* **Scan lists.** Listen to a group of talkgroups, a single talkgroup, or a single radio (unit). Logged in users can build their own lists.
* **Full history.** Page back through older calls, open a call's details, and (for users you allow) download the audio.
* **Emergency calls** are highlighted.
* **Incidents** group the calls about one event so they can be replayed in order.
* **Several recorders.** When two recorders capture the same call, it is only listed once.
* **Accounts.** The site can be open to anyone, invite only, or restricted per talkgroup. Google sign in is optional.

Contents: [Quick start](#quick-start-docker) · [Adding calls](#adding-calls-from-trunk-recorder) ·
[Running the site](#running-the-site) · [Settings](#settings) · [Updating](#updating) ·
[Without Docker](#installing-without-docker) · [Development](#development)


Quick start (Docker)
--------------------

You need [Docker](https://docs.docker.com/get-docker/) with the compose plugin.

```console
git clone https://github.com/e850205/trunk-player.git
cd trunk-player
cp .env.example .env
```

Edit `.env` and set at least these:

| Setting | What to put |
|---|---|
| `SECRET_KEY` | A long random string, e.g. the output of `openssl rand -base64 48` |
| `POSTGRES_PASSWORD` | Any password, it is only used between the containers |
| `ADMIN_PASSWORD` | Password for the `admin` account created on first start |
| `TZ` | Your time zone, e.g. `America/Chicago` |

Then start it:

```console
docker compose up -d --build
```

Open http://localhost and log in as `admin`. The site also answers on https://localhost:8443, with a self-signed certificate.
The admin area at `/admin/` is where you set up talkgroups, scan lists and users.

The database is kept in a Docker volume, so it survives restarts and rebuilds.
Audio files live in the `audio_files` folder next to `docker-compose.yml`. Set `AUDIO_DIR` in `.env` to use another folder.


Adding calls from trunk-recorder
--------------------------------

Every call needs two things:

* **The audio file** (mp3 or m4a) in the audio folder. The site plays it from `/audio_files/`.
* **A record in the database.** Add it with one of the methods below.

**Option 1: the trunk-recorder `.json` file.** Put the audio and the `.json` file trunk-recorder writes next to it in the audio folder, then run:

```console
./manage.py add_transmission audio_files/1200-1700000000_851000000
# with Docker:
docker compose exec app ./manage.py add_transmission audio_files/1200-1700000000_851000000
```

Leave off the file extension. Useful options:

| Option | Use it when |
|---|---|
| `--m4a` | The audio is m4a instead of mp3 |
| `--system N` | The call is from another radio system (the system's ID number in the admin) |
| `--web_url sub/folder/` | The audio is in a subfolder of the audio folder |
| `--queue` | You want the command to return immediately. `./manage.py add_transmission_worker` then adds the call (the Docker image runs one). Good for recorder upload scripts. |

Point trunk-recorder's `uploadScript` at a script that converts the audio to mp3 or m4a, moves it into place, and runs the command.
There are examples in [utility/trunk-recoder/](utility/trunk-recoder/).

**Option 2: the web API.** Handy when trunk-recorder runs on another machine and you copy the audio over yourself.
Set `ADD_TRANS_AUTH_TOKEN` in `.env`, then POST the call as json:

```console
curl -X POST https://scanner.example.com/api_v2/import_transmission/ -d '{
  "auth_token": "<your ADD_TRANS_AUTH_TOKEN>",
  "system": "County P25", "source": "Site 1",
  "talkgroup": 1200, "start_time": 1700000000, "stop_time": 1700000004,
  "freq": 851000000, "emergency": false,
  "audio_filename": "1200-1700000000_851000000", "audio_file_type": "m4a",
  "srcList": [{"src": 1234}, {"src": 5678}] }'
```

`system`, `source`, `talkgroup`, `start_time` and `audio_filename` are required.
Systems, sources, talkgroups and units that don't exist yet are created automatically.

**Talkgroup names.** New talkgroups show up as `#1200` until you name them. Rename them in the admin, or import trunk-recorder's talkgroup file:

```console
./manage.py import_talkgroups --system 1 talkgroups.csv       # --rr for a RadioReference export
```


Running the site
----------------

Most of the setup happens in the admin area (`/admin/`).

* **Scan lists.** Create them under *Scan lists*. Add a list to *Menu scan lists* to put it in the Scan Lists menu, and add talkgroups to *Menu talk group lists* to put them in the Talk Groups menu.
  Logged in users can also make their own lists with *Scan Lists → New Scan List*.
  *Scan Lists → Custom Scan List* lets anyone pick talkgroups on the fly.
* **Unit names.** Calls show unknown radio IDs as `?1234`. Users with the *Can change unit* permission can click the ID to name it.
* **Downloads.** Users with the *Can download audio clips* permission get a *Download audio file* item in each call's menu.
* **Incidents.** In *Transmissions*, tick the calls about an event and choose *Make an incident from the selected calls*, then give it a name and description.
  Incidents are listed under *Incidents*, with a *Listen from start* link.
* **Cities and agencies.** These are a reference list, shown in the *Directory* menu, of which agencies cover which cities.
  Add them in the admin, or import agencies with `./manage.py import_agency`.
  A city can show a map: paste Google Maps' *Embed a map* code or its link.
* **Who can see what.**
  * Talkgroups not marked *public* are only visible to staff.
  * With `ACCESS_TG_RESTRICT=True`, users only see the talkgroups in their *Talk group access* groups. Groups marked *default group* are given to new users.
* **Accounts.**
  * Staff can add users in the admin.
  * Set `OPEN_SITE=True` to let people sign up themselves.
  * Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to add *Sign in with Google*.
  * Set the `EMAIL_*` settings so password reset emails can be sent.
* **More than one recorder.** If several recorders (sources) cover the same talkgroup, recordings of one call are listed once. The one shown is the talkgroup's *play source* if you set one, otherwise the longer recording.
  The other copies stay linked from the call's details page.
  After upgrading, run `./manage.py mark_duplicate_calls` once to apply this to older calls.
* **Pages.** The home and About pages are *Web htmls* in the admin (`index` and `about`), and can be edited there.
  A message shown on every page can be set in *Message pop ups*.


Settings
--------

With Docker, settings go in `.env`. Without Docker, set them as environment variables, or override them in `trunk_player/settings_local.py`.

| Setting | Default | |
|---|---|---|
| `SECRET_KEY` | *(required)* | Keep it secret, used to sign logins |
| `SITE_TITLE` | `Trunk-Player` | Name shown in the menu bar |
| `TZ` | `America/Los_Angeles` | Time zone calls are shown in |
| `ALLOWED_HOSTS` | `*` | Host names the site answers to (space separated). Named `DJANGO_ALLOWED_HOSTS` outside Docker |
| `CSRF_TRUSTED_ORIGINS` | | Needed for https, e.g. `https://scanner.example.com`. Without it logging in fails with a CSRF error |
| `FORCE_SECURE` | `False` | Set to `True` when a proxy in front of the site handles https |
| `AUDIO_DIR` | `./audio_files` | (Docker) Folder on this machine with the audio files |
| `AUDIO_URL_BASE` | `/audio_files/` | Where browsers load audio from, e.g. `//s3.amazonaws.com/my-bucket/` |
| `HTTP_PORT` / `HTTPS_PORT` | `80` / `8443` | (Docker) Ports on this machine |
| `ADD_TRANS_AUTH_TOKEN` | | Token for the import API. The API is off until this is set |
| `OPEN_SITE` | `False` | Let anyone create an account |
| `ACCESS_TG_RESTRICT` | `False` | Only show users the talkgroups in their access groups |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | | Sign in with Google. The OAuth redirect URI is `https://<site>/accounts/google/login/callback/` |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | | Mail server. Without one, emails only go to the log |
| `DUPLICATE_CALL_SECONDS` | `3` | Recordings from different recorders starting this close together count as one call. `0` turns it off |
| `TRANS_DATETIME_FORMAT` | `%H:%M:%S %m/%d/%Y` | How call times are shown |
| `GOOGLE_ANALYTICS_PROPERTY_ID` | | Google Analytics 4 ID (`G-...`) |

The full list is in [docs/settings.rst](docs/settings.rst).

**Putting it on the internet.** The simplest setup is a reverse proxy with a real certificate (Caddy, nginx, Traefik, ...) in front of port 80.
Then set `FORCE_SECURE=True`, `ALLOWED_HOSTS=scanner.example.com` and `CSRF_TRUSTED_ORIGINS=https://scanner.example.com`.


Updating
--------

```console
git pull
docker compose up -d --build
```

Database changes are applied automatically when the container starts.
Without Docker, run `pip install -r requirements.txt`, `./manage.py migrate` and `./manage.py collectstatic`, then restart the site.


Installing without Docker
-------------------------

You need Python 3.10–3.12, PostgreSQL, Redis and nginx. See [docs/install.rst](docs/install.rst), then [docs/config_local.rst](docs/config_local.rst) for nginx and [docs/supervisor.rst](docs/supervisor.rst) to run it as a service.

The site itself is one process, `daphne trunk_player.asgi:application --port 7055`. It serves the pages and the live updates, and nginx sits in front of it to serve the audio and static files.


Development
-----------

```console
python3 -m venv env && . env/bin/activate
pip install -r requirements.txt
sudo apt install redis-server        # live updates need redis
export DEBUG=1
./manage.py migrate
./manage.py createsuperuser
./manage.py runserver
```

This uses SQLite and serves everything, including live updates and `audio_files/`, on http://localhost:8000.
`docker compose -f docker-compose-devel.yml up` does the same with Postgres, and reloads when you edit code.

Run the tests with `./manage.py test`. Most of the site is in `radio/`: models, views and the player script `radio/static/radio/js/trunkplayer.js`.


License and credits
-------------------

MIT licensed, see [License.txt](License.txt). Trunk Player was started by Dylan Reinhold as [ScanOC/trunk-player](https://github.com/ScanOC/trunk-player).
