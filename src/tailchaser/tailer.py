"""Module that contains the the chaser (producer) classes.

.. moduleauthor:: Thanos Vassilakis <thanosv@gmail.com>

"""
import argparse
import binascii
import glob
import gzip

# import hashlib
try:
    import bz2
except ImportError:
    bz2 = None
import logging.handlers
import os
import platform
import pickle
import regex
import shutil
import sys
import tempfile
import time
import collections
import six

log = logging.getLogger(__name__)

SIG_SZ = 256


def slugify(value):
    """
    Parameters
    ----------
    value: str
        the value to slug
    Convert spaces to hyphens.
    Remove characters that aren't alphanumerics, underscores, or hyphens.
    Convert to lowercase. Also strip leading and trailing whitespace.
    """
    value = regex.sub('[^\w\s-]', '', value).strip().lower()
    return regex.sub('[-\s]+', '-', value)


class Tailer(object):
    VERBOSE = False
    DONT_FOLLOW = False
    DRYRUN = False
    DONT_BACKFILL = False
    READ_PERIOD = 1
    CLEAR_CHECKPOINT = False
    READ_PAUSE = 1
    TMP_DIR = None
    ONLY_BACKFILL = False
    INIT_CHECKPOINT = ('', 0, 0)
    STARTING = 'STARTING'
    STOPPED = 'STOPPED'
    RUNNING = 'RUNNING'
    WAITING = 'WAITING'
    ARGS = ('only_backfill', 'dont_backfill', 'read_period', 'clear_checkpoint',
            'read_pause', 'temp_dir', 'start_of_record_re')

    def __init__(self,
                 only_backfill=ONLY_BACKFILL,
                 dont_backfill=DONT_BACKFILL,
                 read_period=READ_PERIOD,
                 clear_checkpoint=CLEAR_CHECKPOINT,
                 read_pause=READ_PAUSE,
                 temp_dir=TMP_DIR,
                 start_of_record_re=None,
                 windows=None):

        self.config = collections.namedtuple('Args', self.ARGS)
        self.config.dont_backfill = dont_backfill
        self.config.only_backfill = only_backfill
        self.config.clear_checkpoint = clear_checkpoint
        self.config.read_period = read_period
        self.config.read_pause = read_pause
        self.config.temp_dir = temp_dir if temp_dir else tempfile.mkdtemp()
        self.config.windows = windows if windows is not None else self.is_windows()
        if start_of_record_re:
            self.config.start_of_record_re = regex.compile(start_of_record_re)
            self.read_record = self.read_record_with_regex
        self.state = self.STARTING
        self.stats = collections.Counter()

    def startup(self):
        pass

    def shutdown(self):
        pass

    def at_eof(self, tmp_file,  is_backfill_file_info):
        if is_backfill_file_info:
            is_backfill, (file_tailed, (fid, mtime, offset)) = is_backfill_file_info
            if is_backfill and tmp_file != file_tailed:
                os.unlink(tmp_file)

    def run(self, source_pattern, receiver=None):
        self.startup()
        self.config.checkpoint_filename = self.make_checkpoint_filename(source_pattern)
        file_tailed = None
        if self.config.clear_checkpoint and os.path.exists(self.config.checkpoint_filename):
            os.unlink(self.config.checkpoint_filename)
        file_info = 'Not Assigned'
        try:
            while self.state != self.STOPPED:
                ticks = time.time()
                try:
                    checkpoint = self.load_checkpoint()
                    is_backfill_file_info = self.next_to_process(source_pattern, checkpoint)
                    print is_backfill_file_info
                    if is_backfill_file_info:
                        is_backfill, file_info = is_backfill_file_info
                        is_backfill = is_backfill or self.config.only_backfill
                        if file_info:
                            if is_backfill or self.config.only_backfill:
                                producer = self.backfill(file_info)
                            else:
                                producer = self.tail(file_info)
                            for file_tailed, checkpoint, record in producer:
                                self.handoff(file_info[0], checkpoint, record, receiver)
                                self.save_checkpoint(checkpoint)
                                if not (self.config.only_backfill or is_backfill) and self.config.read_period:
                                    time_spent = time.time() - ticks
                                    if time_spent > self.config.read_period:
                                        time.sleep(self.config.read_pause)
                                        break
                    elif self.config.only_backfill:
                        break
                except KeyboardInterrupt:
                    raise
                except:
                    raise
                time.sleep(1)
                self.at_eof(file_tailed, is_backfill_file_info)
        finally:
            self.shutdown()

    def handoff(self, file_tailed, checkpoint, record, receiver=None):
        if receiver:
            receiver.send((file_tailed, checkpoint, record))
        else:
            sys.stdout.write(record)

    def next_to_process(self, source_pattern, checkpoint):
        log.debug("next_to_process: %s %s", source_pattern, checkpoint)
        with_stats = [(file_name, os.stat(file_name)) for file_name in glob.glob(source_pattern)]
        # log.debug("with_stats: %s", glob.glob(source_pattern))
        for pos, (file_name, stat) in enumerate(sorted(with_stats, key=lambda x: x[1].st_mtime)):
            # print pos, (file_name, stat), self.make_sig(file_name, stat)
            if stat.st_mtime > checkpoint[1]:
                # print 'younger', (stat.st_mtime > checkpoint[1], stat.st_mtime, checkpoint[1])
                sig = self.make_sig(file_name, stat)
                if sig != checkpoint[0]:
                    # print 'new file'
                    checkpoint = (sig, stat.st_mtime, 0)
                else:
                    if checkpoint[2] == stat.st_size:
                        continue
                    # print 'same as before'
                    checkpoint = (sig, stat.st_mtime, checkpoint[2])
                self.state = 'RUNNING'
                return (pos + 1) != len(with_stats), (file_name, checkpoint)
            elif stat.st_mtime == checkpoint[1]:
                if (pos + 1) != len(with_stats):
                    continue
                sig = self.make_sig(file_name, stat)
                if sig == checkpoint[0]:
                    if stat.st_size == checkpoint[2]:
                        if self.state == self.RUNNING:
                            self.state = self.WAITING
                            return
                checkpoint = (checkpoint[0], stat.st_mtime, checkpoint[2])
                return (pos + 1) != len(with_stats), (file_name, checkpoint)

    def backfill(self, file_info):
        file_to_process, (sig, st_mtime, offset) = file_info
        log.debug("backfill: %s %s", file_to_process, offset)
        copied_file_path = self.copy(file_to_process, self.config.temp_dir)
        for offset, record in self.process(copied_file_path, sig, st_mtime, offset):
            if not record:
                break
            yield copied_file_path, (sig, st_mtime, offset), record

    def tail(self, file_info):
        file_to_process, (sig, st_mtime, offset) = file_info
        log.debug("tail: %s %s", file_to_process, offset)
        while True:
            offset, record = six.next(self.process(file_to_process, sig, st_mtime, offset))
            if record:
                yield self.make_sig(file_to_process), (sig, st_mtime, offset), record

    def process(self, filename, sig, st_mtime, offset):
        with self.file_opener(filename) as file_to_tail:
            log.debug("seeking: %s %s %s", filename, offset, sig)
            file_to_tail.seek(offset, 0)
            for offset, record in self.read_record(file_to_tail):
                yield offset, record

    def read_record(self, file_to_tail):
        byte_read = file_to_tail.tell()
        for record in file_to_tail:
            byte_read += len(record)
            yield byte_read, record

    @staticmethod
    def make_checkpoint_filename(source_pattern, path=None):
        if not path:
            path = os.path.join(os.path.expanduser("~"), '.tailchase')
        if not os.path.exists(path):
            log.debug("making checkpoint path: %s", path)
            os.makedirs(path)
        return os.path.join(path, os.path.basename(slugify(source_pattern) + '.checkpoint'))

    @classmethod
    def file_opener(cls, file_name, mode='rb'):
        if file_name.endswith('.gz'):
            log.debug("gzip file: %s", file_name)
            return gzip.open(file_name, mode)
        elif file_name.endswith('.bz2'):
            if bz2:
                return bz2.BZ2File(file_name, mode)
            else:
                raise NotImplementedError()
        else:
            return open(file_name, mode)

    # def copy(self, src, dst):
    #     log.debug("copying: %s to %s", src, dst)
    #     if src.endswith('.gz'):
    #         log.debug("gzip file: %s", src)
    #         with gzip.open(src, 'rb') as src_fh:
    #             with open(dst, 'wb') as dst_fh:
    #                 return shutil.copyfileobj(src_fh, dst_fh)
    #     elif src.endswith('.gz'):
    #         with bz2.BZ2File(src, 'rb') as src_fh:
    #             with open(dst, 'wb') as dst_fh:
    #                 return shutil.copyfileobj(src_fh, dst_fh)
    #     return shutil.copy2(src, dst)
    @classmethod
    def copy(cls, src, temp_dir):
        log.debug("copying: %s to %s", src, temp_dir)
        stats = os.stat(src)
        with cls.file_opener(src, 'rb') as src_fh:
            sig = cls.sig(src_fh)
            src_fh.seek(0, 0)
            dst = os.path.join(temp_dir, sig)
            with open(dst, 'wb') as dst_fh:
                shutil.copyfileobj(src_fh, dst_fh)
        os.utime(dst, (stats.st_ctime, stats.st_mtime))
        return dst

    @classmethod
    def make_sig(cls, file_to_check, stat=None):
        with cls.file_opener(file_to_check) as fh:
            return cls.sig(fh)
            # return hashlib.sha224(open(file_to_check).read(SIG_SZ)).hexdigest()

    @classmethod
    def sig(cls, file_to_check_fh, stat=None):
        return str(binascii.crc32(file_to_check_fh.read(SIG_SZ)) & 0xffffffff)

    def load_checkpoint(self):
        checkpoint_filename = self.config.checkpoint_filename
        try:
            sig, mtime, offset = pickle.load(open(checkpoint_filename, 'rb'))
            log.debug('loaded: %s %s', checkpoint_filename, (sig, mtime, offset))
            return sig, mtime, offset
        except (IOError, EOFError):
            log.debug('failed to load: %s', checkpoint_filename)
            return self.INIT_CHECKPOINT

    def save_checkpoint(self, checkpoint):
        log.debug('dumping %s %s', self.config.checkpoint_filename, checkpoint)
        return pickle.dump(checkpoint, open(self.config.checkpoint_filename, 'wb'))

    def read_record_with_regex(self, file_to_grep):
        buff = ''
        first_record = True
        e = 0
        s = 0
        offset = file_to_grep.tell()
        while True:
            data = file_to_grep.read(100000)
            if not data:
                break
            buff += data

            while True:
                match = self.config.start_of_record_re.search(buff, e - s)
                if not match:
                    break
                s, e = match.span(0)
                if first_record:
                    first_record = False
                    continue
                offset += len(buff[:s])
                yield offset, buff[:s]
                buff = buff[s:]
                if not buff:
                    break
        offset += len(buff)
        yield offset, buff

    @staticmethod
    def is_windows():
        return 'win' in platform.system().lower()

    @classmethod
    def build_arg_parser(cls, parser=None):
        if not parser:
            parser = argparse.ArgumentParser(description='The ultimate tailer.')
        parser.add_argument('--windows', action='store_true', default=Tailer.is_windows(),
                            help='run as if the platform is windows, default: %s' % Tailer.is_windows())
        parser.add_argument('file-pattern',
                            help='file pattern to tail, such as /var/log/access.*')
        parser.add_argument('--only-backfill', action='store_true', default=Tailer.ONLY_BACKFILL,
                            help='don\'t tail, default: %s' % Tailer.ONLY_BACKFILL)
        parser.add_argument('--dont-backfill', action='store_true', default=Tailer.DONT_BACKFILL,
                            help='basically only tail, default: %s' % Tailer.DONT_BACKFILL)
        parser.add_argument('--clear-checkpoint', action='store_true', default=Tailer.CLEAR_CHECKPOINT,
                            help='start form the beginning, default: %s' % Tailer.CLEAR_CHECKPOINT)
        parser.add_argument('--read-period', type=int, default=Tailer.READ_PERIOD,
                            help='how long you read before you pause.' +
                                 'If zero you don\'t pause, default: %s' % Tailer.READ_PERIOD)
        parser.add_argument('--read-pause', type=int, default=Tailer.READ_PAUSE,
                            help='how long you pause between reads, default: %s' % Tailer.READ_PAUSE)
        parser.add_argument('--reading-from', choices=['unix', 'win'], default='win',
                            help='sets how long you rad and then pause, default: win')
        parser.add_argument('--temp-dir', default=Tailer.TMP_DIR,
                            help='on backfil files are copied to a temp directory.' +
                                 'Use this to set this directory, default: %s' % Tailer.TMP_DIR)
        parser.add_argument('--logging', choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'], default='ERROR',
                            help='logging level, default: ERROR')
        parser.add_argument('--start-of-record-re', default=None,
                            help='use this regex expresion to define the start of a record, default: None')
        parser.add_argument('--show-config', action='store_true', default=False,
                            help='dump-configuration')
        return parser

    @classmethod
    def cli(cls, argv=sys.argv, parser=None, consumer=None):
        arg_parser = cls.build_arg_parser(parser)
        args = vars(arg_parser.parse_args(argv[1:]))
        file_pattern = args.pop('file-pattern')
        reading_from = args.pop('reading_from')
        logging_level = getattr(logging, args.pop('logging'))
        if reading_from == 'win':
            args['read_pause'] = 1
            args['read_period'] = 1
        else:
            args['read_pause'] = 0
            args['read_period'] = 0
        show_config = args.pop('show_config')
        tailer = cls(**args)
        if show_config:
            import pprint
            pprint.pprint(vars(tailer.config))
            return
        logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging_level)
        return tailer.run(file_pattern, consumer)
