Trunk Player
============

### Version 0.1.4

Python Django web frontend for playing recorded radio transmissions. The audio files are recorded using [Trunk Recorder](https://github.com/robotastic/trunk-recorder).

![Main Screen](docs/images/trunk_player_main.png?raw=true "Main Screen")

## Quick start with Docker

You need [Docker](https://docs.docker.com/get-docker/) with the compose plugin.

```console
git clone https://github.com/e850205/trunk-player.git
cd trunk-player
cp .env.example .env
```

Edit `.env` and set at least `SECRET_KEY`, `POSTGRES_PASSWORD` and `ADMIN_PASSWORD`, then:

```console
docker compose up -d --build
```

Open http://localhost (or https://localhost:8443 with a self-signed certificate) and log in with the admin account from `.env`. The admin area is at `/admin/`.

The database lives in a docker volume, so it survives restarts and rebuilds. Audio files go in the `audio_files` folder (set `AUDIO_DIR` in `.env` to use another folder).

Useful commands:

```console
docker compose logs -f app                             # see what is going on
docker compose run --rm app ./manage.py createsuperuser  # add another admin
git pull && docker compose up -d --build               # update to the latest code
```

## Getting calls into Trunk Player

Each call needs its audio file (mp3 or m4a) in the audio folder and a record in the database. Either:

* Put the audio and trunk-recorder `.json` file in the audio folder and run
  `./manage.py add_transmission <file name without extension>`
  (with Docker: `docker compose exec app ./manage.py add_transmission ...`), see `utility/trunk-recoder/` for sample scripts.
* Or POST the call details as json to `/api_v2/import_transmission/`. Set `ADD_TRANS_AUTH_TOKEN` first:

  ```console
  curl -X POST http://localhost/api_v2/import_transmission/ -d '{
    "auth_token": "your ADD_TRANS_AUTH_TOKEN", "system": "My System", "source": "0",
    "talkgroup": 1200, "start_time": 1700000000, "stop_time": 1700000004,
    "freq": 851000000, "audio_filename": "1200-1700000000_851000000",
    "audio_file_type": "m4a", "srcList": [{"src": 1234}] }'
  ```

Browsers showing that talkgroup, scan list or unit update live.

## Development

```console
python3 -m venv env && . env/bin/activate
pip install -r requirements.txt
sudo apt install redis-server      # live updates need redis
export DEBUG=1
./manage.py migrate
./manage.py createsuperuser
./manage.py runserver
```

This uses SQLite and serves everything (pages, websockets and `audio_files/`) from http://localhost:8000. Run the tests with `./manage.py test`.

## Install without Docker

See [docs/install.rst](docs/install.rst). Documents are also at Read the Docs [http://trunk-player.readthedocs.io/](http://trunk-player.readthedocs.io/)

## Using with Unitrunker/EDACS Systems
Check out https://github.com/MaxwellDPS/Unibridge for using Trunk-Player with unitrunker

## License
 - Trunk Player is licensed under the [MIT License](License.txt)
