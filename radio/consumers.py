import re
import logging

from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync

log = logging.getLogger(__name__)

# Page types a browser can listen to, see radio.models.live_call_groups()
GROUP_TYPES = ('scan', 'tg', 'unit')
# Channels group names may only use these characters
VALID_LABEL = re.compile(r'^[a-z0-9_.-]{1,80}$')
MAX_LABELS = 200


def group_name(tg_type, label):
    return 'livecall-{}-{}'.format(tg_type, label)


class RadioConsumer(WebsocketConsumer):
    """Tells the browser when a new transmission arrives for the page it is on.

    The browser connects to /ws-calls/<type>/<label1+label2...> and receives a
    small json message for each new call, it then reloads its call list.
    """

    def connect(self):
        self.groups_joined = []
        kwargs = self.scope.get('url_route', {}).get('kwargs', {})
        tg_type = kwargs.get('tg_type', '')
        label = kwargs.get('label', '')

        if tg_type in GROUP_TYPES:
            labels = {l for l in label.lower().split('+') if VALID_LABEL.match(l)}
            for new_label in sorted(labels)[:MAX_LABELS]:
                name = group_name(tg_type, new_label)
                async_to_sync(self.channel_layer.group_add)(name, self.channel_name)
                self.groups_joined.append(name)
            log.debug('User %s listening to %s', self.scope.get('user'), self.groups_joined)
        else:
            # Accept anyway so the javascript does not keep trying to reconnect
            log.debug('User %s invalid ws path %s', self.scope.get('user'), self.scope.get('path'))

        self.accept()

    def disconnect(self, close_code):
        for name in getattr(self, 'groups_joined', []):
            async_to_sync(self.channel_layer.group_discard)(name, self.channel_name)

    def receive(self, text_data=None, bytes_data=None):
        # The browser does not send us anything we act on
        pass

    def radio_message(self, event):
        self.send(text_data=event['text'])
