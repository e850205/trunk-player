import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from radio.models import Agency, City, System, TalkGroup


class Command(BaseCommand):
    help = 'Import talkgroup labels with their agency and city, and which agencies serve each city'

    def add_arguments(self, parser):
        parser.add_argument('--system', type=int, required=True, help='System the talkgroups belong to')
        parser.add_argument('--talkgroups', help='CSV with columns dec_id,alpha_tag,description,mode,service_type,agency,agency_short,city')
        parser.add_argument('--cities', help='CSV with columns city,police,fire,ems (agency names)')

    def handle(self, *args, **options):
        try:
            system = System.objects.get(pk=options['system'])
        except System.DoesNotExist:
            raise CommandError('System #{} does not exist'.format(options['system']))
        with transaction.atomic():
            if options['talkgroups']:
                self.import_talkgroups(system, options['talkgroups'])
            if options['cities']:
                self.import_cities(options['cities'])

    def import_talkgroups(self, system, file_name):
        alpha_len = TalkGroup._meta.get_field('alpha_tag').max_length
        desc_len = TalkGroup._meta.get_field('description').max_length
        count = 0
        with open(file_name, newline='') as f:
            for row in csv.DictReader(f):
                tg, created = TalkGroup.objects.get_or_create(
                    dec_id=int(row['dec_id']), system=system,
                    defaults={'alpha_tag': row['alpha_tag'][:alpha_len]})
                tg.alpha_tag = row['alpha_tag'][:alpha_len]
                tg.description = row['description'][:desc_len]
                if row.get('mode'):
                    tg.mode = row['mode']
                tg.agency = get_agency(row['agency'], row.get('agency_short'))
                tg.city = get_city(row['city'])
                if row.get('service_type'):
                    tg.service_type = row['service_type'][:100]
                tg.save()
                count += 1
        self.stdout.write('Imported {} talkgroups'.format(count))

    def import_cities(self, file_name):
        count = 0
        with open(file_name, newline='') as f:
            for row in csv.DictReader(f):
                city = get_city(row['city'])
                city.police_service = get_agency(row.get('police'))
                city.fire_service = get_agency(row.get('fire'))
                city.ems_service = get_agency(row.get('ems'))
                city.save()
                count += 1
        self.stdout.write('Imported {} cities'.format(count))


def get_agency(name, short=None):
    if not name:
        return None
    agency = Agency.objects.filter(name=name).first()
    if agency:
        if short and agency.short != short and not Agency.objects.filter(short=short).exists():
            agency.short = short
            agency.save()
        return agency
    short = short or ''.join(word[0] for word in name.split() if word[0].isalnum()).upper()
    unique_short, n = short, 2
    while Agency.objects.filter(short=unique_short).exists():
        unique_short = '{}{}'.format(short, n)
        n += 1
    return Agency.objects.create(name=name, short=unique_short)


def get_city(name):
    if not name:
        return None
    city, created = City.objects.get_or_create(name=name)
    return city
