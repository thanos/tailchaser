"""Module that contains the the chaser (producer) classes.

.. moduleauthor:: Thanos Vassilakis <thanosv@gmail.com>

"""

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
import pickle
import re
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
    Convert spaces to hyphens.
    Remove characters that aren't alphanumerics, underscores, or hyphens.
    Convert to lowercase. Also strip leading and trailing whitespace.
    """
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('[-\s]+', '-', value)


class Tailer(object):
    VERBOSE = False
    DONT_FOLLOW = False
    DRYRUN = False
    DONT_BACKFILL = False
    READ_PERIOD = 1
    CLEAR_CHECKPOINT = False
    READ_PAUSE = 0
    TMP_DIR = None
    ONLY_BACKFILL = False

    STARTING = 'STARTING'
    STOPPED = 'STOPPED'
    RUNNING = 'RUNNING'
    WAITING = 'WAITING'
    ARGS = ('only_backfill', 'dont_backfill', 'read_period', 'clear_checkpoint', 'read_pause', 'temp_dir')

    def __init__(self,
                 only_backfill=ONLY_BACKFILL,
                 dont_backfill=DONT_BACKFILL,
                 read_period=READ_PERIOD,
                 clear_checkpoint=CLEAR_CHECKPOINT,
                 read_pause=READ_PAUSE,
                 temp_dir=TMP_DIR):

        self.config = collections.namedtuple('Args', self.ARGS)
        self.config.dont_backfill = dont_backfill
        self.config.only_backfill = only_backfill
        self.config.clear_checkpoint = clear_checkpoint
        self.config.read_period = read_period
        self.config.read_pause = read_pause
        self.config.temp_dir = temp_dir if temp_dir else tempfile.mkdtemp()
        self.state = self.STARTING
        self.stats = collections.Counter()

    def startup(self):
        pass

    def shutdown(self):
        pass

    def at_eof(self):
        pass

    def run(self, source_pattern, receiver=None):
        self.startup()
        self.config.checkpoint_filename = self.make_checkpoint_filename(source_pattern)
        if self.config.clear_checkpoint and os.path.exists(self.config.checkpoint_filename):
            os.unlink(self.config.checkpoint_filename)
        file_info = 'Not Assigned'
        try:
            while self.state != self.STOPPED:
                ticks = time.time()
                try:
                    checkpoint = self.load_checkpoint()
                    is_backfill_file_info = self.next_to_process(source_pattern, checkpoint)
                    if is_backfill_file_info:
                        is_backfill, file_info = is_backfill_file_info
                        if file_info:
                            if is_backfill or self.config.only_backfill:
                                producer = self.backfill(file_info)
                            else:
                                producer = self.tail(file_info)
                            for file_tailed, checkpoint, record in producer:
                                self.handoff(file_tailed, checkpoint, record, receiver)
                                self.save_checkpoint(checkpoint)
                                if not is_backfill and self.config.read_period:
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
                time.sleep(3)
                self.at_eof()
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
                    # print 'same as before'
                    checkpoint = (sig, stat.st_mtime, checkpoint[2])
                self.state = 'RUNNING'
                return (pos + 1) != len(with_stats), (file_name, checkpoint)
            elif stat.st_mtime == checkpoint[1]:
                if (pos + 1) != len(with_stats):
                    continue
                sig = self.make_sig(file_name, stat)
                if sig == checkpoint[0]:
                    if self.state == self.RUNNING:
                        self.state = self.WAITING
                        return
                checkpoint = (checkpoint[0], stat.st_mtime, checkpoint[2])
                return (pos + 1) != len(with_stats), (file_name, checkpoint)

    def backfill(self, file_info):
        file_to_process, (sig, st_mtime, offset) = file_info
        log.debug("backfill: %s %s", file_to_process, offset)
        copied_file_path = os.path.join(self.config.temp_dir, str(sig))
        self.copy(file_to_process, copied_file_path)
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
                yield "%d" % self.make_sig(file_to_process), (sig, st_mtime, offset), record

    def process(self, filename, sig, st_mtime, offset):
        with open(filename) as file_to_tail:
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

    def copy(self, src, dst):
        log.debug("copying: %s to %s", src, dst)
        with self.file_opener(src, 'rb') as src_fh:
            with open(dst, 'wb') as dst_fh:
                return shutil.copyfileobj(src_fh, dst_fh)

    @classmethod
    def make_sig(cls, file_to_check, stat=None):
        return binascii.crc32(six.b(open(file_to_check).read(SIG_SZ))) & 0xffffffff
        # return hashlib.sha224(open(file_to_check).read(SIG_SZ)).hexdigest()

    def load_checkpoint(self):
        checkpoint_filename = self.config.checkpoint_filename
        try:
            sig, mtime, offset = pickle.load(open(checkpoint_filename, 'rb'))
            log.debug('loaded: %s %s', checkpoint_filename, (sig, mtime, offset))
            return sig, mtime, offset
        except (IOError, EOFError):
            log.debug('failed to load: %s', checkpoint_filename)
            return '', 0, 0

    def save_checkpoint(self, checkpoint):
        log.debug('dumping %s %s', self.config.checkpoint_filename, checkpoint)
        return pickle.dump(checkpoint, open(self.config.checkpoint_filename, 'wb'))
