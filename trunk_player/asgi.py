import os
from django.urls import re_path
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trunk_player.settings")
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

from radio.consumers import RadioConsumer

application = ProtocolTypeRouter({
    "http": django_asgi_app,

    # Live call notifications, see radio/consumers.py
    "websocket": AuthMiddlewareStack(
        URLRouter([
            re_path(r"^ws-calls/(?P<tg_type>[^/]+)/(?P<label>[^/]+)/?$", RadioConsumer.as_asgi()),
            re_path(r"^ws-calls/", RadioConsumer.as_asgi()),
        ])
    ),
})

# Older docs and configs start daphne with trunk_player.asgi:channel_layer
channel_layer = application
