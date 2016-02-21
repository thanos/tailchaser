"""Module that contains the the chaser (producer) classes.

.. moduleauthor:: Thanos Vassilakis <thanosv@gmail.com>

"""


class Producer(object):
    """Base producer class.

    """


import cPickle as pickle
import os
import sys
from collections import namedtuple
import unicodedata
import re
import time
import glob
import hashlib

SIG_SZ=256

def slugify(value):
    """
    Convert spaces to hyphens.
    Remove characters that aren't alphanumerics, underscores, or hyphens.
    Convert to lowercase. Also strip leading and trailing whitespace.
    """
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('[-\s]+', '-', value)


class Tailer(Producer):
    def __init__(self, source_pattern, verbose=False):
        self.args = namedtuple('Args', 'source_pattern, verbose')
        self.args.source_pattern = source_pattern
        self.args.verbose = verbose
        self.checkpoint_filename = self.make_checkpoint_filename(self.args.source_pattern)
        
            #print open(file_to_check, 'r').read(250)

    def handoff(self, file_tailed, checkpoint, record):
        if self.args.verbose:
                path = os.path.join('testoutput', os.path.basename(file_tailed))
                open(path,'a').write(record)
                print file_tailed, checkpoint, record
        return record

    def make_checkpoint_filename(self, source_pattern):
        return os.path.join(os.path.basename(slugify(source_pattern+'.checkpoint'))) 

    def should_tail(self, file_to_check, checkpoint):
        if self.args.verbose: print 'should_tail', file_to_check, checkpoint
        stat = os.stat(file_to_check)
        if self.args.verbose: print stat
        sig = self.make_sig(file_to_check, stat)
        if not checkpoint:
            if self.args.verbose: print 'No Checkpoit',
            return file_to_check,  (sig,  stat.st_ctime, 0)
        if self.args.verbose: print 'should_tail', file_to_check, checkpoint, sig == checkpoint[0]
        if sig == checkpoint[0] and checkpoint[2] < stat.st_size:
            retval =   file_to_check, checkpoint
            if self.args.verbose: print 'SIG the same', retval
            return retval
        if stat.st_mtime > checkpoint[1]:
            if self.args.verbose: print " Younger", file_to_check, (sig,  stat.st_mtime,  0)
            return file_to_check, (sig, stat.st_mtime, 0)
        print 'skipping', file_to_check, (sig, stat.st_ctime, 0)

    def make_sig(self, file_to_check, stat):
        return hashlib.sha224(open(file_to_check).read(SIG_SZ)).hexdigest()

    def load_checkpoint(self, checkpoint_filename):
        try:
            sig, mtime,    offset =  pickle.load(open(checkpoint_filename))
            if self.args.verbose: print 'loading', checkpoint_filename, (sig, mtime,    offset)
            return  sig, mtime,    offset
        except (IOError,EOFError, ValueError):
            return '',0,0

    def save_checkpoint(self, checkpoint_filename, checkpoint):
        if self.args.verbose:print 'dumping', checkpoint_filename, checkpoint
        return pickle.dump(checkpoint, open(checkpoint_filename, 'wb'))

    def tail(self):
        checkpoint = self.load_checkpoint(self.checkpoint_filename)
        while True:
            try:
                print  glob.glob(self.args.source_pattern)
                to_tail = filter(None, sorted((self.should_tail(file_to_check, checkpoint) for file_to_check in glob.glob(self.args.source_pattern)), key=lambda x: x[1][1] if x else x))
                if self.args.verbose: print 'checkpoint', checkpoint
                if self.args.verbose: print 'to_tail', to_tail
                if self.args.verbose: time.sleep(5)
                file_to_tail, checkpoint = to_tail[0]
                to_tail = to_tail[1:]
                
                #raw_input()
                for offset, record in self.process(file_to_tail, checkpoint):
                    self.handoff(file_to_tail, checkpoint, record)
                    checkpoint = checkpoint[0], checkpoint[1], offset
                    self.save_checkpoint(self.checkpoint_filename, checkpoint)
            except KeyboardInterrupt:
                return
            except:
                import traceback
                traceback.print_exc()
            finally:
                self.save_checkpoint(self.checkpoint_filename, checkpoint)
            time.sleep(5)

    def process(self, filename, (sig, st_mtime,  offset)):
        with open(filename, 'rb') as file_to_tail:
            if self.args.verbose: print 'offset', offset
            
            file_to_tail.seek(offset, 0)
            if self.args.verbose: print file_to_tail.tell()
            #raw_input()
            while True:
                record = self.read_record(file_to_tail)
                if not record:
                        break
                else:
                    yield file_to_tail.tell(), record

    def read_record(self, file_to_tail):
        return file_to_tail.readline()


if __name__ =='__main__':
    print sys.argv[1]
    Tailer(sys.argv[1], verbose=True).tail()
