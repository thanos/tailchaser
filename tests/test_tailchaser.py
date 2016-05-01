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


def cmp_file(src_file, dst_file):
    six.print_('testing: ', src_file, dst_file)
    assert (Tailer.file_opener(src_file, 'rb').read() == Tailer.file_opener(dst_file, 'rb').read())


def cmp_files(src_path, dst_path, make_name=os.path.basename):
    src_files = glob.glob(src_path)
    for src_file_path in src_files:
        dst_file_path = os.path.join(dst_path, make_name(src_file_path))
        cmp_file(src_file_path, dst_file_path)


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
    ROLL_DELAY = 2
    EMIT_DELAY = 1
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
    def generate(cls, log_file_path, emits, max_bytes=1024, backup_count=100):
        count = 0
        logger = logging.getLogger(__file__)
        handler = cls(log_file_path, maxBytes=max_bytes, backupCount=backup_count, encoding=cls.ENCODING)
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s  %(name)-12s %(message)s')
        handler.setFormatter(formatter)
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
        self.mode = 'wb'
        self.stream = self._open()


class MultiLineLogHandler(logging.FileHandler):
    ROLL_DELAY = 10
    EMIT_DELAY = .01
    ENCODING = None

    @classmethod
    def generate(cls, log_file_path, emits):
        count = 0
        logger = logging.getLogger(__file__)
        handler = cls(log_file_path, encoding=cls.ENCODING)
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s  %(name)-12s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        while count < emits:
            try:
                count += 1
                if count % 2 == 0:
                    raise NameError("error %08d" % count)
                logger.error("No Exception Thrown: %08d", count)
            except NameError:
                logger.exception("Exception Thrown: %08d", count)


TEST_PATH = os.path.dirname(os.path.abspath(__file__))

BACKFILL_EMITS = 50


def test_backfill(log_handler=RotatingWithDelayFileHandler, consumer=None, tail_to_dir=None, vargs=None):
    tail_from_dir = tempfile.mkdtemp(prefix='tail-test_backfill-tail_from_dir')
    six.print_('generating log files', tail_from_dir)
    log_handler.generate(os.path.join(tail_from_dir, 'test.log'), BACKFILL_EMITS)
    if not tail_to_dir:
        tail_to_dir = tempfile.mkdtemp(prefix='tail-test_backfill-tail_to_dir')

    if not consumer:
        def consumer_gen():
            while True:
                record = yield ()
                open(os.path.join(tail_to_dir, record[1][0]), 'ab').write(record[2])

        consumer = consumer_gen()
        consumer.send(None)
    six.print_('start tailer', tail_to_dir)
    source_pattern = os.path.join(tail_from_dir, '*')
    if not vargs:
        vargs = [__name__, '--only-backfill', '--clear-checkpoint']
    vargs.append(source_pattern)
    main(vargs, consumer)
    cmp_files(source_pattern, tail_to_dir, lambda x: Tailer.make_sig(x))
    six.print_('all done', tail_to_dir)
    # for src_file_path in glob.glob(source_pattern):
    #     dst_file_path = os.path.join(tail_to_dir, Tailer.make_sig(src_file_path))
    #     six.print_("testing:", src_file_path, dst_file_path)
    #     assert (Tailer.file_opener(src_file_path).read() == Tailer.file_opener(dst_file_path).read())


def test_gzip_backfill():
    test_backfill(RotatingGzipFileHandler)


tailed_records = 0


def test_multiline_records():
    tail_to_dir = tempfile.mkdtemp(prefix='ml')

    def consumer_gen(path):
        global tailed_records
        while True:
            record = yield ()
            tailed_records += 1
            open(os.path.join(path, record[1][0]), 'ab').write(record[2])

    consumer = consumer_gen(tail_to_dir)
    consumer.send(None)
    start_of_record_re = '\d{4}-\d{2}-\d{2}'
    vargs = [__name__, '--only-backfill', '--clear-checkpoint', "--start-of-record-re=%s" % start_of_record_re]
    test_backfill(MultiLineLogHandler, consumer, tail_to_dir, vargs=vargs)
    six.print_('emimitted %d and  tailed %s' % (BACKFILL_EMITS, tailed_records))
    assert (BACKFILL_EMITS == tailed_records)


#
#
#   test against simple tail
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
            open(log_file_path, 'ab').write("%08d. %s\n" % (count, 'x' * 64))
            time.sleep(0.1)

    loggen_thread = SimpleLogger()
    loggen_thread.start()
    six.print_('logger started')
    copy_dir = tempfile.mkdtemp(prefix='tail-test')
    six.print_(copy_dir)

    def gx():
        while True:
            record = yield ()
            open(os.path.join(copy_dir, record[1][0]), 'ab').write(record[2])

    consumer = gx()
    consumer.send(None)
    tailer = Tailer(only_backfill=False)
    tailer_thread = threading.Thread(target=tailer.run, args=(log_file_path, consumer))

    tailer_lag = 30
    logger_lag = 60
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
    cmp_files(log_file_path, copy_dir, lambda x: str(Tailer.make_sig(x)))





def test_tail_with_break():
    tmp_dir = tempfile.mkdtemp(prefix='tail-test')
    log_file_path = os.path.join(tmp_dir, 'file.log')
    six.print_(log_file_path)

    class SimpleLogger(Logger):
        def __init__(self):
            self.RUNNING = False
            super(SimpleLogger, self).__init__()

        def emit(self, count):
            open(log_file_path, 'ab').write("%08d. %s\n" % (count, 'x' * 64))
            time.sleep(0.1)


    class BreakingTailer(Tailer):
        def __init__(self):
            super(BreakingTailer, self).__init__(only_backfill=False)
            self.interupt =  threading.Event()

        def handoff(self, file_tailed, checkpoint, record, receiver=None):
            if self.interupt.is_set():
                raise SystemExit()
            super(BreakingTailer, self).handoff(file_tailed, checkpoint, record, receiver)

    loggen_thread = SimpleLogger()
    loggen_thread.start()
    six.print_('logger started')
    copy_dir = tempfile.mkdtemp(prefix='tail-test')
    six.print_(copy_dir)

    def gx():
        while True:
            record = yield ()
            open(os.path.join(copy_dir, record[1][0]), 'ab').write(record[2])

    consumer = gx()
    consumer.send(None)
    tailer = BreakingTailer()
    tailer_thread = threading.Thread(target=tailer.run, args=(log_file_path, consumer))
    tailer_lag = 40
    logger_lag = 80
    loggen_thread.join(tailer_lag)
    six.print_('logger run more than %d secs, start tailer' % tailer_lag)
    tailer_thread.start()
    six.print_('tail started')
    six.print_('run logger %d secs more' % (logger_lag - tailer_lag))
    loggen_thread.join(logger_lag - tailer_lag-20)
    six.print_('stopping tailer')
    tailer.interupt.set()
    six.print_('waiting for tailer to stop')
    loggen_thread.join(5)
    six.print_('tailer stoped - staring again')
    tailer = BreakingTailer()
    tailer_thread = threading.Thread(target=tailer.run, args=(log_file_path, consumer))
    tailer_thread.start()
    loggen_thread.join(logger_lag - tailer_lag)
    loggen_thread.RUNNING = False
    if loggen_thread.is_alive():
        loggen_thread.join()
    six.print_('logger stopped')
    tailer_thread.join(10)
    six.print_('wait for tailer to idle')
    log_files = glob.glob(os.path.join(tmp_dir, '*'))
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
    cmp_files(log_file_path, copy_dir, lambda x: str(Tailer.make_sig(x)))



#
#
#   test file drop senario
#


def test_file_drop():
    drop_file_name = 'drop_file.txt'
    src_file = os.path.join(tempfile.mkdtemp(prefix='test_file_drop-src'), drop_file_name)
    dst_file = os.path.join(tempfile.mkdtemp(prefix='test_file_drop-dst'), drop_file_name)

    def tail_writer():
        while True:
            file_name, checkpoint, record = yield ()
            open(dst_file, 'ab').write(record)

    consumer = tail_writer()
    consumer.send(None)
    tailer = Tailer()
    six.print_("start watch for drop file:", src_file)
    six.print_("will save to:", dst_file)
    tailer_thread = threading.Thread(target=tailer.run, args=(src_file, consumer))
    tailer_thread.start()
    tailer_thread.join(10)

    def file_drop(num_lines=250):
        with open(src_file, 'wb') as dump:
            for count in range(num_lines):
                dump.write("%08d. %s\n" % (count + 1, 'x' * 64))

    dump_thread = threading.Thread(target=file_drop)
    dump_thread.start()
    dump_thread.join()
    six.print_('file dropped')
    tailer_thread.join(10)

    while True:
        six.print_('checking for drop file ingest')
        if tailer.state == tailer.WAITING and os.path.exists(dst_file):
            break
        time.sleep(1)

    six.print_('pickup complete')
    six.print_('stop tailer')
    tailer.state = tailer.STOPPED
    tailer_thread.join()
    six.print_('tailer stopped')
    assert (open(src_file, 'rb').read() == open(dst_file, 'rb').read())
    cmp_files(src_file, dst_file, lambda x: x)


#
#
#   test against rotating log
#

def test_rotating_log():
    tmp_dir = tempfile.mkdtemp(prefix='tail-test')
    log_file_path = os.path.join(tmp_dir, 'file.log')
    six.print_(log_file_path)

    class FastRotate(RotatingWithDelayFileHandler):
        EMIT_DELAY = 0.3
        ROLL_DELAY = 4

    class RotatingLogger(Logger):

        def __init__(self):
            self.RUNNING = False
            self.logger = logging.getLogger(__file__)
            handler = FastRotate(log_file_path, maxBytes=2048,
                                 backupCount=100)
            self.logger.addHandler(handler)
            super(RotatingLogger, self).__init__()

        def emit(self, count):
            self.logger.error("%08d. %s", count, 'x' * 256)

    loggen_thread = RotatingLogger()
    loggen_thread.start()
    six.print_('logger started')
    copy_dir = tempfile.mkdtemp(prefix='tail-test')
    six.print_(copy_dir)

    def gx():
        while True:
            record = yield ()
            open(os.path.join(copy_dir, record[1][0]), 'ab').write(record[2])

    consumer = gx()
    consumer.send(None)
    tailer = Tailer(only_backfill=False, read_pause=2)
    tailer_thread = threading.Thread(target=tailer.run, args=(os.path.join(tmp_dir, '*'), consumer))

    tailer_lag = 20
    logger_run = 40
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
        six.print_('log files %d == files processed %d --> %s' % (len(log_files), len(glob.glob(copy_pattern)),
                                                                  tailer.state))
        if tailer.state == tailer.WAITING and len(log_files) <= len(glob.glob(copy_pattern)):
            break
        time.sleep(1)
    six.print_('stop tailer')
    tailer.state = tailer.STOPPED
    tailer_thread.join()
    six.print_('tailer stopped')

    for src_file_path in log_files:
        dst_file_path = os.path.join(copy_dir, str(Tailer.make_sig(src_file_path)))
        assert (open(src_file_path).read() == open(dst_file_path).read())

        # cmp_files(tmp_dir, copy_dir, lambda x: str(Tailer.make_sig(x)))


if __name__ == '__main__':
    test_backfill()
