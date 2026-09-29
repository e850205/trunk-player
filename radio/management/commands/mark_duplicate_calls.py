from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from radio.models import Transmission


class Command(BaseCommand):
    help = ('Find calls recorded by more than one recorder (source) and hide the extra copies. '
            'New calls are checked as they are added, this is for calls added before that.')

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='How far back to look, 0 for everything (default 30)')

    def handle(self, *args, **options):
        if not settings.DUPLICATE_CALL_SECONDS:
            self.stdout.write('DUPLICATE_CALL_SECONDS is 0, nothing to do')
            return
        calls = Transmission.objects.filter(duplicate_of__isnull=True).select_related('talkgroup_info').order_by('pk')
        if options['days']:
            calls = calls.filter(start_datetime__gte=timezone.now() - timedelta(days=options['days']))
        marked = 0
        for call in calls.iterator():
            call.refresh_from_db(fields=['duplicate_of'])
            if call.duplicate_of_id:
                continue  # hidden earlier in this run
            other = call.find_same_call()
            if other is None:
                continue
            if call.better_recording_than(other):
                call.replace(other)
            else:
                other.replace(call)
            marked += 1
        self.stdout.write('Hid {} duplicate recording{}'.format(marked, '' if marked == 1 else 's'))
