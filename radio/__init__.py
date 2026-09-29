import logging

from django.utils.version import get_version
import os
from subprocess import check_output, CalledProcessError, DEVNULL

logger = logging.getLogger(__name__)


VERSION = (0, 1, 4, 'beta', 1)

__version__ = get_version(VERSION)

try:
    __git_hash__ = check_output(['git', 'rev-parse', '--short', 'HEAD'], stderr=DEVNULL,
                                cwd=os.path.dirname(os.path.abspath(__file__))).strip().decode()
except (FileNotFoundError, CalledProcessError):
    __git_hash__ = '0'

__fullversion__ = '{} #{}'.format(__version__,__git_hash__)

logger.info('Trunk-Player Version ' + __fullversion__)
