import json
import logging
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections, transaction
from redis.exceptions import RedisError

from radio.management.commands.add_transmission import add_new_trans, default_options
from radio.utility import RedisQueue

log = logging.getLogger(__name__)

QUEUE_NAME = 'new_trans'


def parse_job(item):
    """Turn a queued job into add_transmission options

    Jobs are json from "add_transmission --queue", older scripts push
    "json_name:/path/file|system:1|m4a" strings which are still accepted.
    """
    text = item.decode('utf-8') if isinstance(item, bytes) else item
    options = default_options()
    try:
        job = json.loads(text)
    except ValueError:
        job = {}
        for part in text.split('|'):
            key, sep, value = part.partition(':')
            job[key] = value if sep else True
    if 'm4a' in job:  # old name for the option
        job['m4a_file'] = job.pop('m4a')
    options.update(job)
    for key in ('source', 'system'):
        options[key] = int(options[key])
    for key in ('vhf', 'verbose', 'm4a_file'):
        if isinstance(options[key], str):
            options[key] = options[key].lower() in ('1', 'true', 'yes', '')
    return options


class Command(BaseCommand):
    help = 'Add transmissions queued with "add_transmission --queue", runs until stopped'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exit-on-error',
            action='store_true',
            dest='exitonerror',
            default=False,
            help='Exit if a transmission can not be added'
        )

    def handle(self, *args, **options):
        q = RedisQueue(QUEUE_NAME)
        self.stdout.write('Waiting for transmissions')
        while True:
            try:
                item = q.get(timeout=30)
            except RedisError as e:
                self.stderr.write('Redis error, is it running? {}'.format(e))
                time.sleep(5)
                continue
            except KeyboardInterrupt:
                return
            if not item:
                continue
            close_old_connections()
            try:
                job = parse_job(item)
                with transaction.atomic():
                    add_new_trans(job)
                self.stdout.write('Added {}'.format(job['json_name']))
            except Exception:
                log.exception('Unable to add transmission %s', item)
                self.stderr.write('Unable to add transmission {}'.format(item))
                if options['exitonerror']:
                    raise
