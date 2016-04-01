import logging
import os

import six

from tailchaser.cli import main_loggenerator
# from tailchaser.producers import LogGenerator
from tailchaser.tailer import Tailer

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)


def test_loggenerator():
    assert main_loggenerator(['LogGenerator', 'test.log', '--record_number=256', '--message_size=64',
                              '--max_log_size=2048', '--tmp_dir']) == 0


def test_tailer():
    # pattern = LogGenerator.cli(['tests', 'test.log', '--record_number=256', '--message_size=64',
    #                            '--max_log_size=1048', '--tmp_dir'])

    def fx():
        while True:
            record = yield()
            six.print_(record)

    def gx():
        while True:
            record = yield()
            open(os.path.basename(record[0]) + '.2', 'ab').write(record[2])
    f = fx()
    f.send(None)
    Tailer(only_backfill=True, clear_checkpoint=True).run('/var/log/opendirectoryd*', f)

    # os.unlink(Tailer.make_checkpoint_filename(pattern))
    # assert main(['tests', pattern, '--dont_follow']) == 0
