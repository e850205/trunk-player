import json
import re
from pathlib import Path

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from radio.models import ScanList, System, TalkGroup, Transmission, TranmissionUnit, Unit

IN_MEMORY_LAYER = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}


def make_transmission(tg):
    return Transmission.objects.create(
        start_datetime=timezone.now(),
        audio_file='100-1511023743_8.57213e+08',
        talkgroup=tg.dec_id,
        talkgroup_info=tg,
        freq=0,
    )


class ReadOnlyApiTests(TestCase):
    def setUp(self):
        self.tg = TalkGroup.objects.create(dec_id=100, alpha_tag='Test TG 1')

    def test_talkgroups_cannot_be_changed(self):
        self.assertEqual(self.client.post('/api_v1/talkgroups/', {'dec_id': 5, 'alpha_tag': 'x'}).status_code, 405)
        self.assertEqual(self.client.delete('/api_v1/talkgroups/{}/'.format(self.tg.pk)).status_code, 405)
        self.assertTrue(TalkGroup.objects.filter(pk=self.tg.pk).exists())

    def test_scanlists_cannot_be_created(self):
        self.assertEqual(self.client.post('/api_v1/scanlist/', {'name': 'x'}).status_code, 405)

    def test_unknown_scan_list_is_404(self):
        self.assertEqual(self.client.get('/api_v1/scan/does-not-exist/').status_code, 404)

    def test_default_scan_list(self):
        make_transmission(self.tg)
        data = self.client.get('/api_v1/scan/default/').json()
        self.assertEqual(data['count'], 1)

    def test_unknown_incident_is_404(self):
        self.assertEqual(self.client.get('/api_v1/inc/does-not-exist/').status_code, 404)

    def test_unknown_page_is_404(self):
        self.assertEqual(self.client.get('/page/does-not-exist/').status_code, 404)


class ProfileTests(TestCase):
    def setUp(self):
        User.objects.create_user('user1', 'user1@example.com', 'pass1')
        self.client.login(username='user1', password='pass1')

    def test_invalid_profile_post_shows_form(self):
        response = self.client.post('/profile/', {'username': 'user1', 'email': 'not an email'})
        self.assertEqual(response.status_code, 200)

    def test_user_scan_list_page(self):
        self.assertEqual(self.client.get('/userscanlist/').status_code, 200)


@override_settings(ADD_TRANS_AUTH_TOKEN='secret-token', CHANNEL_LAYERS=IN_MEMORY_LAYER)
class ImportTransmissionTests(TestCase):
    url = '/api_v2/import_transmission/'

    def post(self, data):
        return self.client.post(self.url, json.dumps(data), content_type='application/json')

    def valid(self, **extra):
        data = {'auth_token': 'secret-token', 'system': 'Sys', 'source': 'Src', 'talkgroup': 100,
                'start_time': 1700000000, 'stop_time': 1700000004, 'audio_filename': 'file',
                'freq': '851000000', 'srcList': [{'src': 1234}, 5678]}
        data.update(extra)
        return data

    def test_adds_transmission_and_units(self):
        response = self.post(self.valid())
        self.assertEqual(response.status_code, 200)
        t = Transmission.objects.get()
        self.assertEqual(t.play_length, 4)
        self.assertEqual(list(t.units.order_by('tranmissionunit__order').values_list('dec_id', flat=True)), [1234, 5678])

    def test_bad_token(self):
        self.assertEqual(self.post(self.valid(auth_token='wrong')).status_code, 401)

    @override_settings(ADD_TRANS_AUTH_TOKEN='7cf5857c61284')
    def test_default_token_refused(self):
        self.assertEqual(self.post(self.valid(auth_token='7cf5857c61284')).status_code, 401)

    def test_bad_input_is_400(self):
        self.assertEqual(self.client.post(self.url, 'not json', content_type='application/json').status_code, 400)
        data = self.valid()
        del data['start_time']
        self.assertEqual(self.post(data).status_code, 400)
        self.assertEqual(self.post(self.valid(talkgroup='abc')).status_code, 400)
        self.assertFalse(Transmission.objects.exists())

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class LiveCallGroupTests(TestCase):
    """New calls are sent to every page that shows them"""

    def setUp(self):
        self.layer = get_channel_layer()
        self.channel = async_to_sync(self.layer.new_channel)()
        user = User.objects.create_user('user1', 'user1@example.com', 'pass1')
        self.tg = TalkGroup.objects.create(dec_id=100, alpha_tag='Fire Disp')
        scan = ScanList.objects.create(name='Fire', description='Fire', created_by=user)
        scan.talkgroups.add(self.tg)

    def listen(self, group):
        async_to_sync(self.layer.group_add)(group, self.channel)

    def received(self):
        queue = self.layer.channels.get(self.channel)
        count = queue.qsize() if queue else 0
        return [async_to_sync(self.layer.receive)(self.channel) for _ in range(count)]

    def test_scan_list_page_gets_call(self):
        self.listen('livecall-scan-fire')
        make_transmission(self.tg)
        self.assertEqual(len(self.received()), 1)

    def test_default_scan_page_gets_call(self):
        self.listen('livecall-scan-default')
        make_transmission(self.tg)
        self.assertEqual(len(self.received()), 1)

    def test_talkgroup_page_gets_call(self):
        self.listen('livecall-tg-fire-disp')
        make_transmission(self.tg)
        message = self.received()[0]
        self.assertEqual(json.loads(message['text'])['talkgroup_slug'], 'fire-disp')

    def test_other_talkgroup_page_does_not(self):
        self.listen('livecall-tg-other')
        make_transmission(self.tg)
        self.assertEqual(self.received(), [])

    def test_unit_page_gets_call(self):
        self.listen('livecall-unit-1234')
        t = make_transmission(self.tg)
        unit = Unit.objects.create(dec_id=1234, system=System.objects.get(pk=0))
        TranmissionUnit.objects.create(transmission=t, unit=unit, order=0)
        self.assertEqual(len(self.received()), 1)

    def test_edit_does_not_resend(self):
        t = make_transmission(self.tg)
        self.listen('livecall-scan-default')
        t.save()
        self.assertEqual(self.received(), [])


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class ConsumerTests(SimpleTestCase):

    def test_listens_to_each_talkgroup(self):
        from trunk_player.asgi import application

        async def run():
            communicator = WebsocketCommunicator(application, '/ws-calls/tg/one+two/')
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            layer = get_channel_layer()
            await layer.group_send('livecall-tg-two', {'type': 'radio_message', 'text': '{"x": 1}'})
            self.assertEqual(await communicator.receive_from(), '{"x": 1}')
            await communicator.disconnect()
            self.assertEqual(layer.groups.get('livecall-tg-two', {}), {})

        async_to_sync(run)()

    def test_bad_path_still_connects(self):
        from trunk_player.asgi import application

        async def run():
            communicator = WebsocketCommunicator(application, '/ws-calls/about/')
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.disconnect()

        async_to_sync(run)()


class TemplateLayoutTests(TestCase):
    def test_sidebars_have_small_screen_width(self):
        """A column without a small screen width covers the page between
        768 and 991 pixels wide and makes everything under it unclickable"""
        templates = Path(__file__).resolve().parent.parent / 'templates'
        for template in templates.rglob('*.html'):
            for classes in re.findall(r'class="([^"]*col-md-[^"]*)"', template.read_text()):
                self.assertTrue(re.search(r'col-(xs|sm)-', classes), '{}: "{}"'.format(template.name, classes))
