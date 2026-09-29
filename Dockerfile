FROM python:3.12

RUN apt-get update && \
    apt-get -y install --no-install-recommends nginx redis-server ssl-cert tzdata && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/trunkplayer /var/log/trunk-player
WORKDIR /app/trunkplayer

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# install dependencies
COPY requirements.txt /app/trunkplayer/
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Self signed certificate for https on port 443
RUN make-ssl-cert generate-default-snakeoil --force-overwrite

# copy project
COPY . /app/trunkplayer
RUN rm -f /etc/nginx/sites-enabled/default
COPY trunk_player/trunk_player.nginx.docker /etc/nginx/conf.d/nginx.conf

EXPOSE 80
EXPOSE 443

ENTRYPOINT ["./entrypoint.sh"]
