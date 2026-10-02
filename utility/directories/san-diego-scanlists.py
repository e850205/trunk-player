from django.contrib.auth.models import User
from django.db.models import Q
from radio.models import TalkGroup, ScanList, MenuScanList

owner = User.objects.get(username='admin')
live = TalkGroup.objects.filter(public=True).exclude(mode='E')
def tags(*names):
    q = Q()
    for n in names:
        q |= Q(_service_type__name=n)
    return q
def agencies(*names):
    return Q(agency__name__in=names)
fire_tags = tags('Fire Dispatch', 'Fire-Tac', 'Fire-Talk')
ems_tags = tags('EMS Dispatch', 'EMS-Tac', 'EMS-Talk', 'Hospital')
law_tags = tags('Law Dispatch', 'Law Tac', 'Law Talk')
dispatch_tags = tags('Fire Dispatch', 'EMS Dispatch', 'Law Dispatch', 'Multi-Dispatch')
lifeguards = Q(agency__name__icontains='Lifeguard')
imperial_places = ['Brawley', 'Calexico', 'Calipatria', 'El Centro', 'Holtville', 'Imperial', 'Westmorland', 'Niland', 'Salton City', 'Ocotillo', 'Seeley', 'Heber']
imperial = Q(city__name__in=imperial_places) | Q(agency__name__startswith='Imperial County') | Q(agency__name__in=['Niland Fire District', 'Salton Community Services District'])
city_fd = lambda *cities: agencies(*['{} Fire Department'.format(c) for c in cities])

LISTS = [
    ('dispatch', 'All Dispatch', 'Fire, EMS, law and lifeguard dispatch on both systems', dispatch_tags),
    ('sdfd', 'SDFD Fire/EMS', 'San Diego Fire-Rescue on the city 700 MHz system', Q(system_id=1) & agencies('San Diego Fire-Rescue Department') & (fire_tags | ems_tags)),
    ('metro-fire', 'Metro Zone Fire', 'Metro dispatch: Chula Vista, National City, Coronado, Imperial Beach fire (RCS)',
        Q(system_id=0) & (agencies('San Diego Fire-Rescue (Metro Zone)') | city_fd('Chula Vista', 'National City', 'Coronado', 'Imperial Beach'))),
    ('heartland-fire', 'East County Fire', 'Heartland: El Cajon, La Mesa, Lemon Grove, Santee, Lakeside, Bonita fire (RCS)',
        Q(system_id=0) & agencies('Heartland Fire Communications (Central Zone)', 'Bonita-Sunnyside Fire Protection District')),
    ('county-fire', 'CAL FIRE / County Fire', 'CAL FIRE and San Diego County Fire Protection District (RCS)',
        agencies('CAL FIRE/San Diego County Fire Protection District')),
    ('all-fire', 'All Fire', 'Every fire talkgroup on both systems', fire_tags),
    ('ems-hospitals', 'EMS & Hospitals', 'Ambulance, medical command and hospital talkgroups', ems_tags),
    ('law', 'Law Enforcement', 'Unencrypted law enforcement talkgroups on both systems', law_tags),
    ('lifeguards', 'Lifeguards', 'Lifeguard dispatch and tac on both systems', lifeguards),
    ('mutual-aid', 'Mutual Aid & Emergency Ops', 'Interop, mutual aid, emergency operations and system interties',
        tags('Interop', 'Emergency Ops', 'Multi-Talk') | Q(agency__name='San Diego Fire-Rescue Department', alpha_tag__startswith='SDMA')),
]

import re

# Incident groups: each fire command channel with the tacs that go with it.
# A tac joins the command in the same zone (number) whose description it
# shares the most words with, ties go to the nearest command before it.
STOP = {'fire', 'command', 'tac', 'of', 'incidents', 'south', 'north', 'i', '8', 'the'}
CODE = re.compile(r'^(Command|Tac) (\d+)-?([A-Z])\b\s*-?\s*(.*)$')
def words(text):
    return {w for w in re.findall(r'[a-z0-9]+', text.lower())} - STOP

INCIDENT_AGENCIES = [('SDFD', 'SDFD incident channels'), ('MET', 'Metro Zone incident channels'),
                     ('HCF', 'Heartland incident channels')]
incident_lists = []
for short, section in INCIDENT_AGENCIES:
    commands, tacs = [], []
    for tg in live.filter(agency__short=short):
        m = CODE.match(tg.description or '')
        if m:
            entry = (m.group(2), m.group(3), m.group(4), tg)
            (commands if m.group(1) == 'Command' else tacs).append(entry)
    groups = {(z, l): [] for z, l, _, _ in commands}
    for zone, letter, desc, tg in tacs:
        best, best_score = None, 0
        for cz, cl, cdesc, _ in sorted(commands, key=lambda c: c[1]):
            if cz != zone:
                continue
            if cdesc or desc:
                score = len(words(desc) & words(cdesc))
            else:
                score = 1 if cl < letter else 0  # no descriptions, go by position
            if score > best_score or (score == best_score and score and cl < letter):
                best, best_score = (cz, cl), score
        if best:
            groups[best].append((letter, tg))
    for zone, letter, desc, cmd in sorted(commands, key=lambda c: (int(c[0]), c[1])):
        members = sorted(groups[(zone, letter)], key=lambda m: m[0])
        if not members:
            continue
        label = re.sub(r'\b(Command|Fires?|Incidents)\b', '', desc)
        label = re.sub(r'\s+([,)])', r'\1', re.sub(r'\s+', ' ', label)).strip(' ,-')
        label = label.replace('South of I-8', 'S of I-8').replace('North of I-8', 'N of I-8')
        name = '{} {}{}{}'.format(short, zone, letter, ' ' + label if label else '')[:30].strip()
        tac_codes = ', '.join(zone + l for l, _ in members)
        description = '{} {}{} command with tacs {}'.format(short, zone, letter, tac_codes)
        incident_lists.append((section, name, description, [cmd] + [tg for _, tg in members]))

MenuScanList.objects.all().delete()
ScanList.objects.filter(name='North County Fire').delete()
ScanList.objects.filter(description__contains=' command with tacs ').delete()
order = 0
def add_list(section, name, desc, tgs):
    global order
    order += 1
    sl, _ = ScanList.objects.update_or_create(name=name, defaults={'description': desc, 'created_by': owner, 'public': True})
    sl.talkgroups.set(tgs)
    MenuScanList.objects.create(name=sl, order=order, section=section)
    print('{:30} {:4}  {}'.format(name, len(tgs), desc if section.endswith('channels') else ''))
for slug, name, desc, q in LISTS:
    add_list('', name, desc, list(live.filter(q).distinct()))
for section, name, desc, tgs in incident_lists:
    add_list(section, name, desc, tgs)
