import difflib
import glob
import gzip
import logging
import logging.handlers
import os
import tempfile
import threading
import time

import six

from tailchaser.cli import main
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
        six.print_(count)


class RotatingWithDelayFileHandler(logging.handlers.RotatingFileHandler):
    ROLL_DELAY = 10
    EMIT_DELAY = .01
    rolls = 0
    ENCODING = None

    def doRollover(self):
        time.sleep(self.ROLL_DELAY)
        self.rolls += 1
        six.print_('rolls', self.rolls)
        return super(RotatingWithDelayFileHandler, self).doRollover()

    def emit(self, record):
        time.sleep(self.EMIT_DELAY)
        return super(RotatingWithDelayFileHandler, self).emit(record)

    @classmethod
    def generate(cls, log_file_path, emits, max_bytes=2096 * 5, backup_count=100):
        count = 0
        logger = logging.getLogger(__file__)
        handler = cls(log_file_path, maxBytes=max_bytes, backupCount=backup_count, encoding=cls.ENCODING)
        logger.addHandler(handler)
        while count < emits:
            count += 1
            logger.error("%08d. %s", count, 'x' * 64)


class RotatingGzipFileHandler(RotatingWithDelayFileHandler):
    def doRollover(self):
        """
        Do a rollover, as described in __init__().
        """
        time.sleep(self.ROLL_DELAY)
        if self.stream:
            self.stream.close()
            self.stream = None

        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = "%s.%d.gz" % (self.baseFilename, i)
                dfn = "%s.%d.gz" % (self.baseFilename, i + 1)
                if os.path.exists(sfn):
                    # print "%s -> %s" % (sfn, dfn)
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self.baseFilename + ".1.gz"
            if os.path.exists(dfn):
                os.remove(dfn)
            with open(self.baseFilename, "rb") as sf:
                with gzip.open(dfn, "wb") as df:
                    df.writelines(sf)
            os.remove(self.baseFilename)
            # print "%s -> %s" % (self.baseFilename, dfn)
        self.mode = 'w'
        self.stream = self._open()


TEST_PATH = os.path.dirname(os.path.abspath(__file__))


def test_backfill(log_handler=RotatingWithDelayFileHandler):
    tail_from_dir = tempfile.mkdtemp(prefix='tail-test_backfill-tail_from_dir')
    six.print_('generating log files', tail_from_dir)
    log_handler.generate(os.path.join(tail_from_dir, 'test.log'), 250)
    tail_to_dir = tempfile.mkdtemp(prefix='tail-test_backfill-from_to_dir')

    def gx():
        while True:
            record = yield ()
            open(os.path.join(tail_to_dir, os.path.basename(record[0])), 'ab').write(record[2])

    consumer = gx()
    consumer.send(None)
    six.print_('start tailer', tail_to_dir)

    source_pattern = os.path.join(tail_from_dir, '*')
    main([__name__, '--only-backfill', '--clear-checkpoint', source_pattern], consumer)
    for src_file_path in glob.glob(source_pattern):
        dst_file_path = os.path.join(tail_to_dir, str(Tailer.make_sig(src_file_path)))
        assert (Tailer.file_opener(src_file_path).read() == Tailer.file_opener(dst_file_path).read())


def test_gzip_backfill():
    test_backfill(RotatingGzipFileHandler)


#
#
#   test against simpe tail
#

def test_tail():
    tmp_dir = tempfile.mkdtemp(prefix='tail-test')
    log_file_path = os.path.join(tmp_dir, 'file.log')
    six.print_(log_file_path)

    class SimpleLogger(Logger):
        def __init__(self):
            self.RUNNING = False
            super(SimpleLogger, self).__init__()

        def emit(self, count):
            open(log_file_path, 'a').write("%08d. %s\n" % (count, 'x' * 64))
            time.sleep(0.1)

    loggen_thread = SimpleLogger()
    loggen_thread.start()
    six.print_('logger started')
    copy_dir = tempfile.mkdtemp(prefix='tail-test')
    six.print_(copy_dir)

    def gx():
        while True:
            record = yield ()
            open(os.path.join(copy_dir, os.path.basename(record[0])), 'ab').write(record[2])

    consumer = gx()
    consumer.send(None)
    tailer = Tailer(only_backfill=False)
    tailer_thread = threading.Thread(target=tailer.run, args=(log_file_path, consumer))

    tailer_lag = 40
    logger_lag = 80
    loggen_thread.join(tailer_lag)
    six.print_('logger run more than %d secs, start tailer' % tailer_lag)
    tailer_thread.start()
    six.print_('tail started')
    six.print_('run logger %d secs more' % (logger_lag - tailer_lag))
    loggen_thread.join(logger_lag - tailer_lag)
    six.print_('stop logger')
    loggen_thread.RUNNING = False
    if loggen_thread.is_alive():
        loggen_thread.join()
    log_files = glob.glob(os.path.join(tmp_dir, '*'))
    six.print_('logger stopped')
    tailer_thread.join(5)
    six.print_('wait for tailer to idle')
    copy_pattern = os.path.join(copy_dir, '*')
    while True:
        six.print_('log files %d == files processed %d' % (len(log_files), len(glob.glob(copy_pattern))))
        if tailer.state == tailer.WAITING and len(log_files) == len(glob.glob(copy_pattern)):
            break
        time.sleep(1)
    six.print_('stop tailer')
    tailer.state = tailer.STOPPED
    tailer_thread.join()
    six.print_('tailer stopped')

    dst_file_path = os.path.join(copy_dir, str(Tailer.make_sig(log_file_path)))
    diff = list(difflib.ndiff(open(log_file_path, 'U').readlines(), open(dst_file_path, 'U').readlines()))
    six.print_(diff)
    assert (open(log_file_path).read() == open(dst_file_path).read())


#
#
#   test against rotating log
#


def test_rotating_log():
    tmp_dir = tempfile.mkdtemp(prefix='tail-test')
    log_file_path = os.path.join(tmp_dir, 'file.log')
    six.print_(log_file_path)

    class RotatingLogger(Logger):
        def __init__(self):
            self.RUNNING = False
            self.logger = logging.getLogger(__file__)
            handler = RotatingWithDelayFileHandler(log_file_path, maxBytes=2048,
                                                   backupCount=100)
            self.logger.addHandler(handler)
            super(RotatingLogger, self).__init__()

        def emit(self, count):
            self.logger.error("%08d. %s", count, 'x' * 64)

    loggen_thread = RotatingLogger()
    loggen_thread.start()
    six.print_('logger started')
    copy_dir = tempfile.mkdtemp(prefix='tail-test')
    six.print_(copy_dir)

    def gx():
        while True:
            record = yield ()
            open(os.path.join(copy_dir, os.path.basename(record[0])), 'ab').write(record[2])

    consumer = gx()
    consumer.send(None)
    tailer = Tailer(only_backfill=False)
    tailer_thread = threading.Thread(target=tailer.run, args=(os.path.join(tmp_dir, '*'), consumer))

    tailer_lag = 40
    logger_run = 60
    loggen_thread.join(tailer_lag)
    six.print_('logger run more than %d secs, start tailer' % tailer_lag)
    tailer_thread.start()
    six.print_('tail started')
    six.print_('run logger %d secs more' % (logger_run - tailer_lag))
    loggen_thread.join(logger_run - tailer_lag)
    six.print_('stop logger')
    loggen_thread.RUNNING = False
    if loggen_thread.is_alive():
        loggen_thread.join()
    log_files = glob.glob(os.path.join(tmp_dir, '*'))
    six.print_('logger stopped')
    tailer_thread.join(5)
    six.print_('wait for tailer to idle')
    copy_pattern = os.path.join(copy_dir, '*')
    while True:
        six.print_('log files %d == files processed %d' % (len(log_files), len(glob.glob(copy_pattern))))
        if tailer.state == tailer.WAITING and len(log_files) == len(glob.glob(copy_pattern)):
            break
        time.sleep(1)
    six.print_('stop tailer')
    tailer.state = tailer.STOPPED
    tailer_thread.join()
    six.print_('tailer stopped')

    for src_file_path in log_files:
        dst_file_path = os.path.join(copy_dir, str(Tailer.make_sig(src_file_path)))
        assert (open(src_file_path).read() == open(dst_file_path).read())


if __name__ == '__main__':
    test_rotating_log()
