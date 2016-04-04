import difflib
import glob
import logging
import logging.handlers
import os
import tempfile
import threading
import time

from tailchaser.cli import main_loggenerator, main
from tailchaser.tailer import Tailer


class Logger(threading.Thread):
    def __init__(self):
        self.RUNNING = False
        super(Logger, self).__init__()

    def run(self):
        count = 0
        self.RUNNING = True
        while self.RUNNING:
            count += 1
            self.emit(count)

    def emit(self, count):
        print count


class RotatingWithDelayFileHandler(logging.handlers.RotatingFileHandler):
    ROLL_DELAY = 10
    EMIT_DELAY = .1
    rolls = 0
    
    def doRollover(self):
        time.sleep(self.ROLL_DELAY)
        self.rolls +=1
        print 'rolls', self.rolls
        return super(RotatingWithDelayFileHandler, self).doRollover()

    def emit(self, record):
        time.sleep(self.EMIT_DELAY)
        return super(RotatingWithDelayFileHandler, self).emit(record)
    
    @classmethod
    def generate(cls, log_file_path, emits):
      count = 0
      logger = logging.getLogger(__file__)
      handler = cls(log_file_path, maxBytes=4096*5, backupCount=100)
      logger.addHandler(handler)
      while count < emits:
          count +=1
          logger.error("%08d. %s", count, 'x' * 128)


TEST_PATH = os.path.dirname(os.path.abspath(__file__))


def test_loggenerator():
    assert main_loggenerator(['LogGenerator', 'test.log', '--record_number=256', '--message_size=64',
                              '--max_log_size=2048', '--tmp_dir']) == 0


def test_make_sig():
    assert (Tailer.make_sig(os.path.join(TEST_PATH, 'logs', 'opendirectoryd.log')) == 3472773093)


def test_backfill():
    tail_from_dir = tempfile.mkdtemp(prefix='tail-test_backfill-tail_from_dir')
    print 'generating log files',tail_from_dir
    RotatingWithDelayFileHandler.generate(os.path.join(tail_from_dir,'test.log'), 1000)
    tail_to_dir = tempfile.mkdtemp(prefix='tail-test_backfill-from_to_dir')
    
    def gx():
        while True:
            record = yield ()
            open(os.path.join(tail_to_dir, os.path.basename(record[0])), 'ab').write(record[2])

    consumer = gx()
    consumer.send(None)
    print 'start tailer', tail_to_dir
    
    source_pattern = os.path.join(tail_from_dir,'*')
    main([__name__, '--only-backfill', '--clear-checkpoint', source_pattern], consumer)
    for src_file_path in glob.glob(source_pattern):
        dst_file_path = os.path.join(tail_to_dir, str(Tailer.make_sig(src_file_path)))
        assert (open(src_file_path).read() == open(dst_file_path).read())


#
#
#   test against simpe tail
#

def test_tail():
    tmp_dir = tempfile.mkdtemp(prefix='tail-test')
    log_file_path = os.path.join(tmp_dir, 'file.log')
    print log_file_path

    class SimpleLogger(Logger):
        def __init__(self):
            self.RUNNING = False
            super(SimpleLogger, self).__init__()

        def emit(self, count):
            print >> open(log_file_path, 'a'), "%08d. %s" % (count, 'x' * 128)
            time.sleep(0.1)

    loggen_thread = SimpleLogger()
    loggen_thread.start()
    print 'logger started'
    copy_dir = tempfile.mkdtemp(prefix='tail-test')
    print copy_dir

    def gx():
        while True:
            record = yield ()
            open(os.path.join(copy_dir, os.path.basename(record[0])), 'ab').write(record[2])

    consumer = gx()
    consumer.send(None)
    tailer = Tailer(only_backfill=False)
    tailer_thread = threading.Thread(target=tailer.run, args=(log_file_path, consumer))

    TAILER_LAG = 20
    LOGGER_RUN = 40
    loggen_thread.join(TAILER_LAG)
    print "logger run more than %d secs, start tailer" % TAILER_LAG
    tailer_thread.start()
    print 'tail started'
    # print  logger.RUNNING, loggen_thread.is_alive()
    # # loggen_thread.join(10)
    # print  logger.RUNNING, loggen_thread.is_alive()
    # # logger.RUNNING = False
    # print  logger.RUNNING, loggen_thread.is_alive()
    # if loggen_thread.is_alive():
    #   print 'starting join'
    #
    #
    # print 'logger finished', loggen_thread.is_alive()
    # tailer_thread.join(20)

    print 'run logger %d secs more' % (LOGGER_RUN - TAILER_LAG)
    loggen_thread.join(LOGGER_RUN - TAILER_LAG)
    print 'stop logger'
    loggen_thread.RUNNING = False
    if loggen_thread.is_alive():
        loggen_thread.join()
    print 'logger stopped'
    tailer_thread.join(5)
    print 'wait for tailer to idle'
    while tailer.state != tailer.WAITING:
        pass
    print 'stop tailer'
    tailer.state = tailer.STOPPED
    tailer_thread.join()
    print 'tailer stopped'

    dst_file_path = os.path.join(copy_dir, str(Tailer.make_sig(log_file_path)))
    diff = list(difflib.ndiff(open(log_file_path, 'U').readlines(), open(dst_file_path, 'U').readlines()))
    print diff
    assert (open(log_file_path).read() == open(dst_file_path).read())


#
#
#   test against rotating log
#


def test_rotaing_log():
    tmp_dir = tempfile.mkdtemp(prefix='tail-test')
    log_file_path = os.path.join(tmp_dir, 'file.log')
    print log_file_path

    class RotatingLogger(Logger):
        def __init__(self):
            self.RUNNING = False
            self.logger = logging.getLogger(__file__)
            handler = RotatingWithDelayFileHandler(log_file_path, maxBytes=4096,
                                                   backupCount=100)
            self.logger.addHandler(handler)
            super(RotatingLogger, self).__init__()

        def emit(self, count):
            self.logger.error("%08d. %s", count, 'x' * 128)

    loggen_thread = RotatingLogger()
    loggen_thread.start()
    print 'logger started'
    copy_dir = tempfile.mkdtemp(prefix='tail-test')
    print copy_dir

    def gx():
        while True:
            record = yield ()
            open(os.path.join(copy_dir, os.path.basename(record[0])), 'ab').write(record[2])

    consumer = gx()
    consumer.send(None)
    tailer = Tailer(only_backfill=False)
    tailer_thread = threading.Thread(target=tailer.run, args=(os.path.join(tmp_dir, '*'), consumer))

    TAILER_LAG = 40
    LOGGER_RUN = 80
    loggen_thread.join(TAILER_LAG)
    print "logger run more than %d secs, start tailer" % TAILER_LAG
    tailer_thread.start()
    print 'tail started'
    # print  logger.RUNNING, loggen_thread.is_alive()
    # # loggen_thread.join(10)
    # print  logger.RUNNING, loggen_thread.is_alive()
    # # logger.RUNNING = False
    # print  logger.RUNNING, loggen_thread.is_alive()
    # if loggen_thread.is_alive():
    #   print 'starting join'
    #
    #
    # print 'logger finished', loggen_thread.is_alive()
    # tailer_thread.join(20)

    print 'run logger %d secs more' % (LOGGER_RUN - TAILER_LAG)
    loggen_thread.join(LOGGER_RUN - TAILER_LAG)
    print 'stop logger'
    loggen_thread.RUNNING = False
    if loggen_thread.is_alive():
        loggen_thread.join()
    print 'logger stopped'
    tailer_thread.join(5)
    print 'wait for tailer to idle'
    while tailer.state != tailer.WAITING:
        pass
    print 'stop tailer'
    tailer.state = tailer.STOPPED
    tailer_thread.join()
    print 'tailer stopped'

    for src_file_path in glob.glob(os.path.join(tmp_dir, '*')):
        dst_file_path = os.path.join(copy_dir, str(Tailer.make_sig(src_file_path)))
        assert (open(src_file_path).read() == open(dst_file_path).read())


if __name__ == '__main__':
    test_backfill()
