import json
import os
import tempfile
from datetime import datetime, timezone as dt_timezone

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from radio.management.commands.add_transmission import add_new_trans, default_options
from radio.management.commands.add_transmission_worker import parse_job
from radio.models import Agency, City, Incident, ScanList, System, TalkGroup, Transmission

IN_MEMORY_LAYER = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}


def make_transmission(tg, **extra):
    return Transmission.objects.create(start_datetime=timezone.now(), audio_file='file', talkgroup=tg.dec_id,
                                       talkgroup_info=tg, freq=0, **extra)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER, ACCESS_TG_RESTRICT=False)
class PublicTalkgroupTests(TestCase):
    """Non public talkgroups are hidden everywhere, except from staff"""

    def setUp(self):
        self.public = TalkGroup.objects.create(dec_id=1, alpha_tag='Open')
        self.hidden = TalkGroup.objects.create(dec_id=2, alpha_tag='Secret', public=False)
        self.hidden_call = make_transmission(self.hidden)
        make_transmission(self.public)
        User.objects.create_user('staff', 's@example.com', 'pass', is_staff=True)

    def slugs(self, url):
        return {r['talkgroup_info']['slug'] for r in self.client.get(url).json()['results']}

    def test_hidden_from_everyone(self):
        self.assertEqual(self.slugs('/api_v1/scan/default/'), {'open'})
        self.assertEqual(self.slugs('/api_v1/tg/secret/'), set())
        self.assertEqual(self.client.get('/audio/{}/'.format(self.hidden_call.slug)).status_code, 404)
        self.assertNotContains(self.client.get('/talkgroups/'), 'Secret')
        self.assertNotContains(self.client.get('/scan/default/details/'), 'Secret')

    def test_staff_see_everything(self):
        self.client.login(username='staff', password='pass')
        self.assertEqual(self.slugs('/api_v1/scan/default/'), {'open', 'secret'})
        self.assertEqual(self.client.get('/audio/{}/'.format(self.hidden_call.slug)).status_code, 200)


class TalkgroupSlugTests(TestCase):
    def test_same_name_on_two_systems(self):
        other = System.objects.create(name='County P25')
        first = TalkGroup.objects.create(dec_id=1, alpha_tag='Fire Dispatch')
        second = TalkGroup.objects.create(dec_id=1, alpha_tag='Fire Dispatch', system=other)
        self.assertEqual(first.slug, 'fire-dispatch')
        self.assertEqual(second.slug, 'fire-dispatch-county-p25')
        second.save()
        self.assertEqual(second.slug, 'fire-dispatch-county-p25')

    def test_rename_changes_slug(self):
        tg = TalkGroup.objects.create(dec_id=1, alpha_tag='Fire Dispatch')
        tg.alpha_tag = 'Fire Tac'
        tg.save()
        self.assertEqual(tg.slug, 'fire-tac')

    def test_name_without_letters(self):
        self.assertEqual(TalkGroup.objects.create(dec_id=55, alpha_tag='###').slug, 'tg-55')


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class PageLinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('user1', 'u@example.com', 'pass')
        self.client.login(username='user1', password='pass')
        self.tg = TalkGroup.objects.create(dec_id=1, alpha_tag='Fire Dispatch')

    def test_menu_links(self):
        ScanList.objects.create(name='My Fire', description='My Fire', created_by=self.user)
        page = self.client.get('/talkgroups/')
        for link in ('/inc/', '/city/', '/agency/', '/talkgroups/?recent=1', '/userscanlist/', '/scan/my-fire/'):
            self.assertContains(page, 'href="{}"'.format(link))

    def test_scan_details_by_slug(self):
        scan = ScanList.objects.create(name='Fire Things', description='Fire Things', created_by=self.user)
        scan.talkgroups.add(self.tg)
        page = self.client.get('/scan/fire-things/details/')
        self.assertContains(page, 'Fire Dispatch')
        self.assertEqual(self.client.get('/scan/nope/details/').status_code, 404)

    def test_new_scan_list_goes_to_it(self):
        response = self.client.post('/userscanlist/', {'name': 'Night Shift', 'talkgroups': [self.tg.pk]})
        self.assertRedirects(response, '/scan/night-shift/', fetch_redirect_response=False)

    def test_incident_list(self):
        Incident.objects.create(name='Brush Fire', description='Big one').transmissions.add(make_transmission(self.tg))
        Incident.objects.create(name='Hidden Thing', public=False)
        page = self.client.get('/inc/')
        self.assertContains(page, 'Brush Fire')
        self.assertContains(page, '1 call')
        self.assertNotContains(page, 'Hidden Thing')
        self.assertContains(self.client.get('/inc/brush-fire/'), 'Big one')
        self.assertEqual(self.client.get('/inc/hidden-thing/').status_code, 404)

    def test_cities_and_agencies_link_each_other(self):
        fire = Agency.objects.create(name='County Fire', short='CFD')
        City.objects.create(name='Springfield', fire_service=fire)
        cities = self.client.get('/city/')
        self.assertContains(cities, 'href="/city/springfield/"')
        self.assertContains(cities, 'href="/agency/#agency-cfd"')
        agencies = self.client.get('/agency/')
        self.assertContains(agencies, 'id="agency-cfd"')
        self.assertContains(agencies, 'href="/city/springfield/"')
        self.assertContains(self.client.get('/city/springfield/'), 'County Fire')


class AdminIncidentActionTests(TestCase):
    @override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
    def test_make_incident_from_calls(self):
        User.objects.create_superuser('admin', 'a@example.com', 'pass')
        self.client.login(username='admin', password='pass')
        tg = TalkGroup.objects.create(dec_id=1, alpha_tag='Fire')
        calls = [make_transmission(tg), make_transmission(tg)]
        response = self.client.post('/admin/radio/transmission/', {
            'action': 'make_incident', '_selected_action': [c.pk for c in calls]})
        incident = Incident.objects.get()
        self.assertRedirects(response, '/admin/radio/incident/{}/change/'.format(incident.pk), fetch_redirect_response=False)
        self.assertEqual(incident.transmissions.count(), 2)


class AccountTests(TestCase):
    def test_register_goes_to_signup(self):
        self.assertRedirects(self.client.get('/register/'), '/accounts/signup/', fetch_redirect_response=False)

    @override_settings(OPEN_SITE=False)
    def test_signup_closed(self):
        self.client.post('/accounts/signup/', {'username': 'new', 'email': 'n@example.com',
                                               'password1': 'a-Long-pass-123', 'password2': 'a-Long-pass-123'})
        self.assertFalse(User.objects.filter(username='new').exists())

    @override_settings(OPEN_SITE=True)
    def test_signup_open(self):
        response = self.client.post('/accounts/signup/', {'username': 'new', 'email': 'n@example.com',
                                                          'password1': 'a-Long-pass-123', 'password2': 'a-Long-pass-123'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.get(username='new').profile)

    def test_logout(self):
        User.objects.create_user('user1', 'u@example.com', 'pass')
        self.client.login(username='user1', password='pass')
        self.assertContains(self.client.get('/about/'), 'class="logout-form"')
        self.client.post('/logout/')
        self.assertNotIn('_auth_user_id', self.client.session)


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class ImportTests(TestCase):
    def test_worker_job_formats(self):
        job = parse_job(json.dumps(dict(default_options(), json_name='/a/b', system='2')).encode())
        self.assertEqual((job['json_name'], job['system'], job['source']), ('/a/b', 2, -1))
        old = parse_job(b'json_name:/a/b|system:3|m4a')
        self.assertEqual((old['json_name'], old['system'], old['m4a_file']), ('/a/b', 3, True))

    def test_worker_job_adds_transmission(self):
        with tempfile.TemporaryDirectory() as folder:
            name = os.path.join(folder, '1200-1700000000_851000000')
            with open(name + '.json', 'w') as f:
                json.dump({'freq': 851000000, 'talkgroup': 1200, 'start_time': 1700000000, 'stop_time': 1700000004,
                           'emergency': 1, 'srcList': [{'src': 55}]}, f)
            add_new_trans(parse_job(json.dumps(dict(default_options(), json_name=name))))
        t = Transmission.objects.get()
        self.assertTrue(t.emergency)
        self.assertEqual(t.play_length, 4)
        self.assertEqual(list(t.units.values_list('dec_id', flat=True)), [55])

    @override_settings(TIME_ZONE='America/Chicago')
    def test_vhf_file_time_is_local_time(self):
        options = dict(default_options(), json_name='90002_cnf_20160903_015052', vhf=True, system=0)
        add_new_trans(options)
        # 01:50:52 CDT (UTC-5)
        self.assertEqual(Transmission.objects.get().start_datetime, datetime(2016, 9, 3, 6, 50, 52, tzinfo=dt_timezone.utc))

    def test_vhf_timezone_option(self):
        options = dict(default_options(), json_name='90002_cnf_20160103_015052', vhf=True, system=0,
                       vhf_timezone='America/Los_Angeles')
        add_new_trans(options)
        # 01:50:52 PST (UTC-8)
        self.assertEqual(Transmission.objects.get().start_datetime, datetime(2016, 1, 3, 9, 50, 52, tzinfo=dt_timezone.utc))
