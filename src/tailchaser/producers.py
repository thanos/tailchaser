"""Module that contains the the chaser (producer) classes.

.. moduleauthor:: Thanos Vassilakis <thanosv@gmail.com>

"""

import argparse
import cPickle
import glob
import hashlib
import logging
import logging.handlers
import os
import pprint
import random
import re
import sys
import tempfile
import time
from collections import namedtuple


class Producer(object):
    """Base producer class.

    """

    @classmethod
    def cli(cls, argv=sys.argv):
        arg_parse = cls.add_arguments()
        args = vars(arg_parse.parse_args(argv[1:]))
        # return cls(**args).run()
        # pool = Pool(processes=args['workers'])
        # if len(args[cls.ARGS_TAG]):
        #   return cls(**args).run()
        # pool.map()

        return cls(**args).run()

    @staticmethod
    def console(*args):
        print >> sys.stderr, args


SIG_SZ = 256


def slugify(value):
    """
    Convert spaces to hyphens.
    Remove characters that aren't alphanumerics, underscores, or hyphens.
    Convert to lowercase. Also strip leading and trailing whitespace.
    """
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('[-\s]+', '-', value)


class LogGenerator(Producer):
    FORMAT = '%(asctime)s %(levelname)s  %(module)s %(process)d %(thread)d %(message)s'
    MSG_SIZE = 128
    RECORD_NUMBER = 10 * 1024
    MAX_LOG_SIZE = 1024 * 128
    BACKUP_COUNT = 20
    WRITE_DELAY = 0.1
    TMP_DIR = False

    def __init__(self, log_file_name, record_number=RECORD_NUMBER, max_log_size=MAX_LOG_SIZE, backup_count=BACKUP_COUNT,
                 write_delay=WRITE_DELAY, message_size=MSG_SIZE,
                 tmp_dir=TMP_DIR, log_format=FORMAT):
        self.args = namedtuple('Args', ['log_file_name', 'record_number', 'max_log_size', 'backup_count', 'write_delay',
                                        'tmp_dir', 'log_format', 'message_size'])
        self.args.log_file_name = log_file_name
        self.args.record_number = record_number
        self.args.max_log_size = max_log_size
        self.args.backup_count = backup_count
        self.args.write_delay = write_delay
        self.args.tmp_dir = tmp_dir
        self.args.log_format = log_format
        self.args.tmp_dir = tmp_dir
        self.args.message_size = message_size

    def run(self):
        abs_file_name = os.path.abspath(self.args.log_file_name)
        abs_path, log_file_name = os.path.split(abs_file_name)
        if self.args.tmp_dir:
            abs_path = tempfile.mkdtemp(prefix='tailchaser')
            print >>sys.stderr, (abs_path)
            abs_file_name = os.path.join(abs_path, log_file_name)
        if not os.path.exists(abs_path):
            os.makedirs(abs_path)

        logger = logging.getLogger()
        handler = logging.handlers.RotatingFileHandler(abs_file_name, maxBytes=self.args.max_log_size,
                                                       backupCount=self.args.backup_count)
        handler.setFormatter(logging.Formatter(self.args.log_format))
        logger.addHandler(handler)
        count = 0
        write_delay = self.args.write_delay
        msg = 'X' * self.args.message_size
        ticks = time.time()
        while count < self.args.record_number:
            count += 1
            logger.error("%d - %s", count, msg)
            print time.ctime(), count, count / (time.time() - ticks)
            time.sleep(random.uniform(0, write_delay))
        return os.path.join(abs_path, '*')

    @classmethod
    def add_arguments(cls, parser=None):
        if not parser:
            parser = argparse.ArgumentParser(description='the ultimate tail chaser',
                                             prog='tailer',
                                             usage='%(prog)s [options] source_pattern'
                                             )
            parser.add_argument('log_file_name', help='path to store log files')
            parser.add_argument('--message_size', type=int, default=cls.MSG_SIZE,
                                help='message size: %s' % cls.MSG_SIZE)
            parser.add_argument('--record_number', type=int, default=cls.RECORD_NUMBER,
                                help='max log size before you rotate: %s' % cls.RECORD_NUMBER)
            parser.add_argument('--max_log_size', type=int, default=cls.MAX_LOG_SIZE,
                                help='max log size before you rotate: %s' % cls.MAX_LOG_SIZE)
            parser.add_argument('--backup_count', type=int, default=cls.BACKUP_COUNT,
                                help='max log entries (0= unlimited) : %s' % cls.BACKUP_COUNT)
            parser.add_argument('--write_delay', type=float, default=cls.WRITE_DELAY,
                                help='max log entries (0= unlimited) : %s' % cls.WRITE_DELAY)
            parser.add_argument('--log_format', default=cls.FORMAT, help='flog foromat, default: %s' % cls.FORMAT),
            parser.add_argument('--tmp_dir', action='store_true', default=cls.TMP_DIR,
                                help='dry runs, default is: %s' % cls.TMP_DIR)

        return parser

    @classmethod
    def cli(cls, argv=sys.argv):
        arg_parse = cls.add_arguments()
        return cls(**vars(arg_parse.parse_args(argv[1:]))).run()


class Tailer(Producer):
    VERBOSE = False
    DONT_FOLLOW = False
    DRYRUN = False
    DONT_BACKFILL = False
    READ_PERIOD = 1.0
    CLEAR_CHECKPOINT = False
    READ_PAUSE = 0

    def __init__(self, source_pattern, verbose=VERBOSE, dont_follow=DONT_FOLLOW, dryrun=DRYRUN,
                 dont_backfill=DONT_BACKFILL, read_period=READ_PERIOD, clear_checkpoint=CLEAR_CHECKPOINT,
                 read_pause=READ_PAUSE):
        self.args = namedtuple('Args',
                               ['source_pattern', 'verbose', 'dont_follow', 'dryrun', 'dont_backfill', 'read_period',
                                'clear_checkpoint', 'read_pause'])
        self.args.source_pattern = source_pattern
        self.args.verbose = verbose
        self.args.dont_follow = dont_follow
        self.args.dryrun = dryrun
        self.args.dont_backfill = dont_backfill
        self.args.read_period = read_period
        self.args.clear_checkpoint = clear_checkpoint
        self.args.read_pause = read_pause
        self.checkpoint_filename = self.make_checkpoint_filename(self.args.source_pattern)
        self.stats = (time.time(), 0)
        self.startup()

    def startup(self):
        pass

    def handoff(self, file_tailed, checkpoint, record):
        if self.args.verbose:
            self.console(file_tailed, checkpoint, record)
        else:
            sys.stdout.write(record)
            # self.stats = self.stats[0], self.stats[1] + 1
            # self.console(file_tailed, checkpoint, record, self.stats[1]/(time.time() - self.stats[0]))
        return record

    @staticmethod
    def make_checkpoint_filename(source_pattern, path=None):
        if not path:
            path = os.path.join(os.path.expanduser("~"), '.tailchase')
        if not os.path.exists(path):
            os.makedirs(path)
        return os.path.join(path, os.path.basename(slugify(source_pattern) + '.checkpoint'))

    def should_tail(self, file_to_check, checkpoint):
        if self.args.verbose:
            self.console('testing', file_to_check, checkpoint)
        stat = os.stat(file_to_check)
        if self.args.verbose:
            self.console(stat)
        sig = self.make_sig(file_to_check, stat)
        if not checkpoint:
            if self.args.verbose:
                self.console('No Checkpoint')
            return file_to_check, (sig, stat.st_ctime, 0)
        if sig == checkpoint[0]:
            if checkpoint[2] < stat.st_size:
                retval = file_to_check, checkpoint
                if self.args.verbose:
                    self.console('SIG the same', retval)
                return retval
            else:
                return
        if stat.st_mtime > checkpoint[1]:
            if self.args.verbose:
                self.console(" Younger", file_to_check, (sig, stat.st_mtime, 0))
            return file_to_check, (sig, stat.st_mtime, 0)
        if self.args.verbose:
            self.console('skipping', file_to_check, (sig, stat.st_ctime, 0))

    @classmethod
    def make_sig(cls, file_to_check, stat):
        return hashlib.sha224(open(file_to_check).read(SIG_SZ)).hexdigest()

    def load_checkpoint(self, checkpoint_filename):
        try:
            if self.args.clear_checkpoint:
                return '', 0, 0
            if self.args.verbose:
                print 'loading'
            sig, mtime, offset = cPickle.load(open(checkpoint_filename))
            if self.args.verbose:
                self.console('loaded', checkpoint_filename, (sig, mtime, offset))
            return sig, mtime, offset
        except (IOError, EOFError, ValueError):
            return '', 0, 0

    def save_checkpoint(self, checkpoint_filename, checkpoint):
        if self.args.verbose:
            self.console('dumping', checkpoint_filename, checkpoint)
        return cPickle.dump(checkpoint, open(checkpoint_filename, 'wb'))

    def run(self):
        checkpoint = self.load_checkpoint(self.checkpoint_filename)
        while True:
            try:
                to_tail = filter(None, sorted((self.should_tail(file_to_check, checkpoint)
                                               for file_to_check in glob.glob(self.args.source_pattern)),
                                              key=lambda x: x[1][1] if x else x))
                if not to_tail:
                    if self.args.dont_follow:
                        return
                    else:
                        time.sleep(10)
                        continue
                if self.args.verbose:
                    print "to_tailto_tail"
                    pprint.pprint(to_tail)
                    self.console('checkpoint', checkpoint)
                if self.args.verbose:
                    self.console('to_tail', to_tail)
                if self.args.verbose:
                    time.sleep(5)
                file_to_tail, checkpoint = to_tail[0]
                to_tail = to_tail[1:]
                ticks = time.time()
                while time.time() - ticks < self.args.read_period:
                    offset, record = self.process(file_to_tail, checkpoint).next()
                    self.handoff(file_to_tail, checkpoint, record)
                    checkpoint = checkpoint[0], checkpoint[1], offset
                    self.save_checkpoint(self.checkpoint_filename, checkpoint)

            except KeyboardInterrupt:
                raise
            except:
                import traceback
                traceback.print_exc()
            finally:
                pass  # self.save_checkpoint(self.checkpoint_filename, checkpoint)
            time.sleep(self.args.read_pause)

    def process(self, filename, (sig, st_mtime, offset)):
        with open(filename, 'rb') as file_to_tail:
            if self.args.verbose:
                self.console('offset', offset)
            # raw_input()
            file_to_tail.seek(offset, 0)
            if self.args.verbose:
                self.console(file_to_tail.tell())
            # raw_input()
            for offset, record in self.read_record(file_to_tail):
                yield offset, record

    def read_record(self, file_to_tail):
        bytes = file_to_tail.tell()
        for record in file_to_tail:
            bytes += len(record)
            yield bytes, record

    ARGS_TAG = 'source_pattern'

    @classmethod
    def add_arguments(cls, parser=None):
        if not parser:
            parser = argparse.ArgumentParser(description='the ultimate tail chaser',
                                             prog='tailer',
                                             usage='%(prog)s [options] source_pattern'
                                             )
        parser.add_argument(cls.ARGS_TAG,  # nargs='+',
                            help='source pattern is the glob path to a file to be tailed plus its rotated versions')
        parser.add_argument('--verbose', action='store_true', default=cls.VERBOSE,
                            help='prints a lot crap, default is: %s' % cls.VERBOSE)
        parser.add_argument('--dryrun', action='store_true', default=cls.DRYRUN,
                            help='prints a lot crap and no hand-off, default is: %s' % cls.DRYRUN)
        parser.add_argument('--dont_backfill', action='store_true', default=cls.DONT_BACKFILL,
                            help='don\'t backfill with rolled logs, default is: %s' % cls.DONT_BACKFILL)
        parser.add_argument('--dont_follow', action='store_true', default=cls.DONT_FOLLOW,
                            help='don\'t follow when you reach the end of the file exit, default is: %s'
                                 % cls.DONT_FOLLOW)
        parser.add_argument('--clear_checkpoint', action='store_true', default=cls.CLEAR_CHECKPOINT,
                            help='clears the checkpoint and lets you start from the begining, default:%s'
                                 % cls.CLEAR_CHECKPOINT)
        parser.add_argument('--read_period', type=float, default=cls.READ_PERIOD,
                            help='time given to read, default: %s' % cls.READ_PERIOD)
        parser.add_argument('--read_pause', type=float, default=cls.READ_PAUSE,
                            help='time to pause between reads, default: %s' % cls.READ_PAUSE)
        return parser
