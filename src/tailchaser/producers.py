"""Module that contains the the chaser (producer) classes.

.. moduleauthor:: Thanos Vassilakis <thanosv@gmail.com>

"""

import argparse
import binascii
import glob
import gzip
import hashlib
import logging
import logging.handlers
import os
import random
import re
import shutil
import sys
import tempfile
import time
from collections import namedtuple
from multiprocessing import Pool, cpu_count

log = logging.getLogger(__name__)


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
    FORMAT = '%(asctime)s %(levelname)s %(module)s %(process)d %(thread)d %(message)s'
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
            log.info("tmp dir: %s", abs_path)

            abs_file_name = os.path.join(abs_path, log_file_name)
        if not os.path.exists(abs_path):
            os.makedirs(abs_path)

        log_gen = logging.getLogger()
        handler = logging.handlers.RotatingFileHandler(abs_file_name, maxBytes=self.args.max_log_size,
                                                       backupCount=self.args.backup_count)
        handler.setFormatter(logging.Formatter(self.args.log_format))
        log_gen.addHandler(handler)
        count = 0
        write_delay = self.args.write_delay
        msg = 'X' * self.args.message_size
        ticks = time.time()
        while count < self.args.record_number:
            count += 1
            log_gen.debug("%d - %s", count, msg)
            log.debug("count: %d, rate: %0.02f", count, count / (time.time() - ticks))
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


# class Args:
#     pass
#
#
# class Tailer(Producer):
#     VERBOSE = False
#     DONT_FOLLOW = False
#     DRYRUN = False
#     DONT_BACKFILL = False
#     READ_PERIOD = 1.0
#     CLEAR_CHECKPOINT = False
#     READ_PAUSE = 0
#     WORKERS = cpu_count()
#
#     def __init__(self, source_patterns, verbose=VERBOSE, dont_follow=DONT_FOLLOW, dryrun=DRYRUN,
#                  dont_backfill=DONT_BACKFILL, read_period=READ_PERIOD, clear_checkpoint=CLEAR_CHECKPOINT,
#                  read_pause=READ_PAUSE, workers=WORKERS, log_config=''):
#         self.args = namedtuple('Args',
#                                ['source_patterns', 'verbose', 'dont_follow', 'dryrun', 'dont_backfill', 'read_period',
#                                 'clear_checkpoint', 'read_pause', 'workers', 'log_config'])
#         self.args = Args()
#         self.args.source_patterns = source_patterns
#         self.args.verbose = verbose
#         self.args.dont_follow = dont_follow
#         self.args.dryrun = dryrun
#         self.args.dont_backfill = dont_backfill
#         self.args.read_period = read_period
#         self.args.clear_checkpoint = clear_checkpoint
#         self.args.read_pause = read_pause
#         self.args.workers = workers
#         self.args.log_config = log_config
#         self.stats = (time.time(), 0)
#
#         self.temp_dir = tempfile.mkdtemp()
#         self.records_sent = 0
#
#         self.startup()
#
#     def startup(self):
#         pass
#
#     def start_logging(self):
#         if self.args.log_config:
#             logging.config.fileConfig(self.args.log_config)
#             self.logger = logging.getLogger(__name__)
#         else:
#             logging.basicConfig(level=logging.DEBUG,
#                                 format='%(asctime)s %(levelname)-8s  %(name)-12s  %(message)s',
#                                 datefmt='%m-%d %H:%M',
#                                 filename='/temp/myapp.log',
#                                 filemode='w')
#             # define a Handler which writes INFO messages or higher to the sys.stderr
#             console = logging.StreamHandler()
#             console.setLevel(logging.INFO)
#             # set a format which is simpler for console use
#             formatter = logging.Formatter('%(asctime)s %(levelname)-8s  %(name)-12s %(message)s')
#             # tell the handler to use this format
#             console.setFormatter(formatter)
#             # add the handler to the root logger
#             self.logger = logging.getLogger(__name__)
#             self.logger.addHandler(console)
#         self.startup()
#
#     def handoff(self, file_tailed, checkpoint, record):
#         self.logger.info("handoff: %s %s %s", file_tailed, checkpoint, record)
#         return record
#
#     @staticmethod
#     def make_checkpoint_filename(source_pattern, path=None):
#         if not path:
#             path = os.path.join(os.path.expanduser("~"), '.tailchase')
#         if not os.path.exists(path):
#             logging.getLogger(__name__).logger.info("making checkpoint path: %s", path)
#             os.makedirs(path)
#         return os.path.join(path, os.path.basename(slugify(source_pattern) + '.checkpoint'))
#
#     def open(self, file_name):
#         if file_name.endswith('.gz'):
#             self.logger.info("gzip file: %s", file_name)
#             return gzip.open(file_name, 'rb')
#         else:
#             return open(file_name, 'rb')
#
#     def copy_to_tmp(self, to_copy):
#         to_upload = [(os.path.join(self.temp_dir, checkpoint[0]), checkpoint) for path, checkpoint in to_copy]
#
#         map(self.copy, [path for path, checkpoint in to_copy], [path for path, checkpoint in to_upload])
#         return to_upload
#         # if temp_dir:
#         #     temp_dir
#         # pool = Pool(processes=4)
#         # pool.map(lambda x: shutil.copy2(x, os.path(join(temp_dir, os.path.basename(x)))),  to_copy)
#
#     def copy(self, src, dst):
#         self.logger.info("copying: %s to %s", src, dst)
#         return shutil.copy2(src, dst)
#
#     def should_tail(self, file_to_check, checkpoint):
#         self.logger.debug('testing %s == %s', file_to_check, checkpoint)
#
#         stat = os.stat(file_to_check)
#         self.logger.debug('stat: %s', stat)
#         sig = self.make_sig(file_to_check, stat)
#         if not checkpoint:
#             retval = file_to_check, (sig, stat.st_ctime, 0)
#             self.logger.debug('No Checkpoin %s', retval)
#             return retval
#         if sig == checkpoint[0]:
#             self.logger.debug('same sig')
#             if checkpoint[2] < stat.st_size:
#                 retval = file_to_check, checkpoint
#                 self.logger.debug('same sig but bigger%s', retval)
#                 return retval
#             elif checkpoint[2] == stat.st_size:
#                 self.logger.debug('same sig and size')
#             else:
#                 self.logger.error('same sig but now smaller  %s %s %s', file_to_check, checkpoint[2], stat.st_size)
#
#                 return
#         if stat.st_mtime > checkpoint[1]:
#             self.logger.debug("Younger: %s %s", file_to_check, (sig, stat.st_mtime, 0))
#             return file_to_check, (sig, stat.st_mtime, 0)
#         self.logger.debug('skipping %s %s', file_to_check, (sig, stat.st_ctime, 0))
#
#     @classmethod
#     def make_sig(cls, file_to_check, stat):
#         return binascii.crc32(open(file_to_check).read(SIG_SZ)) & 0xffffffff
#         return hashlib.sha224(open(file_to_check).read(SIG_SZ)).hexdigest()
#
#     def load_checkpoint(self, checkpoint_filename):
#         try:
#             if self.args.clear_checkpoint:
#                 return '', 0, 0
#             self.logger.debug('loading')
#             sig, mtime, offset = cPickle.load(open(checkpoint_filename))
#             self.logger.info('loaded: %s %s', checkpoint_filename, (sig, mtime, offset))
#             return sig, mtime, offset
#         except (IOError, EOFError, ValueError):
#             return '', 0, 0
#
#     def save_checkpoint(self, checkpoint_filename, checkpoint):
#         self.logger.info('dumping %s %s', checkpoint_filename, checkpoint)
#         return cPickle.dump(checkpoint, open(checkpoint_filename, 'wb'))
#
#     def __call__(self, source_pattern):
#         self.start_logging()
#         checkpoint_filename = self.make_checkpoint_filename(source_pattern)
#         checkpoint = self.load_checkpoint(checkpoint_filename)
#         to_process = []
#         self.ticks = 0
#         file_to_tail = 'not assinged'
#         while True:
#             try:
#                 if not to_process:
#                     to_process = filter(None, sorted((self.should_tail(file_to_check, checkpoint)
#                                                       for file_to_check in glob.glob(source_pattern)),
#                                                      key=lambda x: x[1][1] if x else x))
#
#                     to_upload = self.copy_to_tmp(to_process[:-1])
#                     to_process = to_upload + to_process[-1:]
#
#                 self.logger.debug("to process: %s", to_process)
#                 self.logger.debug('checkpoint: %s', checkpoint)
#                 if not to_process:
#                     # if self.args.dont_follow:
#                     #    return
#                     # else:
#
#                     time.sleep(5)
#                     continue
#                 file_to_tail, checkpoint = to_process[0]
#                 to_process = to_process[1:]
#                 ticks = time.time()
#                 while to_process or (time.time() - ticks < self.args.read_period):
#                     offset, record = self.process(file_to_tail, checkpoint).next()
#                     if not record:
#                         break
#                     self.handoff(file_to_tail, checkpoint, record)
#                     self.records_sent += 1
#                     checkpoint = checkpoint[0], checkpoint[1], offset
#                     self.save_checkpoint(checkpoint_filename, checkpoint)
#             except KeyboardInterrupt:
#                 sys.exit()
#             except:
#                 self.logger.exception("error in main loop: %s %s", file_to_tail, checkpoint)
#             finally:
#                 pass  # self.save_checkpoint(self.checkpoint_filename, checkpoint)
#             if not to_process:
#                 time.sleep(self.args.read_pause)
#
#     def process(self, filename, (sig, st_mtime, offset)):
#         with self.open(filename) as file_to_tail:
#             file_to_tail.seek(offset, 0)
#             for offset, record in self.read_record(file_to_tail):
#                 yield offset, record
#
#     def read_record(self, file_to_tail):
#         bytes = file_to_tail.tell()
#         for record in file_to_tail:
#             bytes += len(record)
#             yield bytes, record
#
#     ARGS_TAG = 'source_patterns'
#
#     @classmethod
#     def cli(cls, argv=sys.argv):
#         arg_parse = cls.add_arguments()
#         args = arg_parse.parse_args(argv[1:])
#         if len(args.source_patterns) == 1:
#             cls(**vars(args))(args.source_patterns[1])
#         elif len(args.source_patterns) >= 1:
#             pool = Pool(processes=args.workers)
#             try:
#                 pool.map(cls(**vars(args)), args.source_patterns)
#             except KeyboardInterrupt:
#                 print "Caught KeyboardInterrupt, terminating workers"
#                 pool.terminate()
#                 pool.join()
#             else:
#                 print "Quitting normally"
#                 pool.close()
#                 pool.join()
#
#     @classmethod
#     def add_arguments(cls, parser=None):
#         if not parser:
#             parser = argparse.ArgumentParser(description='the ultimate tail chaser',
#                                              prog='tailer',
#                                              usage='%(prog)s [options] source_pattern'
#                                              )
#         parser.add_argument(cls.ARGS_TAG, nargs='+',
#                             help='source patterns is a list of glob paths to a file to be tailed plus its rotated versions')
#         parser.add_argument('--verbose', action='store_true', default=cls.VERBOSE,
#                             help='prints a lot crap, default is: %s' % cls.VERBOSE)
#         parser.add_argument('--dryrun', action='store_true', default=cls.DRYRUN,
#                             help='prints a lot crap and no hand-off, default is: %s' % cls.DRYRUN)
#         parser.add_argument('--dont_backfill', action='store_true', default=cls.DONT_BACKFILL,
#                             help='don\'t backfill with rolled logs, default is: %s' % cls.DONT_BACKFILL)
#         parser.add_argument('--dont_follow', action='store_true', default=cls.DONT_FOLLOW,
#                             help='don\'t follow when you reach the end of the file exit, default is: %s'
#                                  % cls.DONT_FOLLOW)
#         parser.add_argument('--clear_checkpoint', action='store_true', default=cls.CLEAR_CHECKPOINT,
#                             help='clears the checkpoint and lets you start from the begining, default:%s'
#                                  % cls.CLEAR_CHECKPOINT)
#         parser.add_argument('--read_period', type=float, default=cls.READ_PERIOD,
#                             help='time given to read, default: %s' % cls.READ_PERIOD)
#         parser.add_argument('--read_pause', type=float, default=cls.READ_PAUSE,
#                             help='time to pause between reads, default: %s' % cls.READ_PAUSE)
#         parser.add_argument('--workers', type=int, default=cls.WORKERS,
#                             help='processor pool size, default: %s' % cls.WORKERS)
#         parser.add_argument('--log_config',
#                             help='log configuration file used to override the default settings')
#         return parser
