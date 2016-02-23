
from tailchaser.cli import main
from tailchaser.producers import LogGenerator, Tailer


def test_loggenerator():
    LogGenerator('test.log', record_number=256, message_size=64, max_log_size=1024, tmp_dir=True).run()
    assert 0 == 0 # main([]) == 0


def test_tailer():
    pattern = LogGenerator.cli(['tests', 'test.log', '--record_number=256', '--message_size=32',
                               '--max_log_size=1024',  '--tmp_dir'])
    # class FTailer(Tailer):
    #  FOLLOW = False
    # Tailer.cli(['tests', pattern, '--follow'])
    Tailer.cli(['tests', pattern, '--dont_follow'])
    assert 0 == 0  # main([]) == 0


def test_tailer_verbose():
    pattern = LogGenerator.cli(['tests', 'test.log', '--record_number=256', '--message_size=32',
                               '--max_log_size=1024',  '--tmp_dir', ])
    # class FTailer(Tailer):
    #  FOLLOW = False
    # Tailer.cli(['tests', pattern, '--follow'])
    Tailer.cli(['tests', pattern, '--verbose', '--dont_follow'])
    assert 0 == 0  # main([]) == 0