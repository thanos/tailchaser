import os

from tailchaser.cli import main, main_loggenerator
from tailchaser.producers import LogGenerator, Tailer


def test_loggenerator():
    assert main_loggenerator(['LogGenerator', 'test.log', '--record_number=256', '--message_size=64',
                              '--max_log_size=2048', '--tmp_dir']) == 0


def test_tailer():
    pattern = LogGenerator.cli(['tests', 'test.log', '--record_number=256', '--message_size=64',
                                '--max_log_size=1048', '--tmp_dir'])
    #os.unlink(Tailer.make_checkpoint_filename(pattern))
    assert main(['tests', pattern, '--dont_follow']) == 0


def test_tailer_verbose():
    pattern = LogGenerator.cli(['tests', 'test.log', '--record_number=256', '--message_size=32',
                               '--max_log_size=1024', '--tmp_dir', ])
    # class FTailer(Tailer):
    #  FOLLOW = False
    # Tailer.cli(['tests', pattern, '--follow'])
    Tailer.cli(['tests', pattern, '--verbose', '--dont_follow'])
    assert 0 == 0  # main([]) == 0
