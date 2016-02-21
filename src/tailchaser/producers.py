"""
Module that contains the the chaser (collector) classes.

"""

import os, time, pickle
import argparse, glob

FORMAT = '%(asctime)s %(levelname)s  %(module)s %(process)d %(thread)d %(message)s'
LOGNUM= 1
MAX_LOGS_PER_DIR = max(LOGNUM/10,1)
MAX_LOG_SIZE = 2**10
MSG_SIZE = 2**10
MAX_LOG_ENTRIES = MAX_LOG_SIZE
SIG_SZ = 250

TAILER=None

try:
    from config import *
except ImportError, ie:
    pass



#from pykafka import KafkaClient
import datetime
from multiprocessing import Pool
from Queue import Queue
import threading

import slugify






import hashlib



class Tailer(object):
    def __init__(self, args):
        self.args = args
        print self.args
        self.checkpoint_filename = self.make_checkpoint_filename(self.args.source_pattern)
        
            #print open(file_to_check, 'r').read(250)

    def handoff(self, file_tailed, checkpoint, record):
        if self.args.verbose:
                print file_tailed, checkpoint, record
        return consumer.process(checkpoint, record)



    def make_checkpoint_filename(self, source_pattern):
        return os.path.join(os.path.basename(slugify.slugify(source_pattern+'.checkpoint'))) 

    def should_tail(self, file_to_check, checkpoint):
        if self.args.verbose: print 'should_tail', file_to_check, checkpoint
        stat = os.stat(file_to_check)
        sig = self.make_sig(file_to_check, stat)
        if not checkpoint:
            if self.args.verbose: print 'No Checkpoit',
            return file_to_check,  (sig,  stat.st_mtime, 0)
        print 'should_tail', file_to_check, checkpoint, sig == checkpoint[0]
        if sig == checkpoint[0] and checkpoint[2] < stat.st_size:
            retval =   file_to_check, checkpoint
            if self.args.verbose: print 'SIG the same', retval
            return retval
        if stat.st_mtime > checkpoint[1]:
            if self.args.verbose: print " Younger", file_to_check, (sig,  stat.st_mtime,  0)
            return file_to_check, (sig, stat.st_mtime, 0)
        print 'skipping', file_to_check, (sig, stat.st_mtime, 0)

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

    def process(self, consumer):
        checkpoint = self.load_checkpoint(self.checkpoint_filename)
        while True:
            try:
                to_tail = filter(None, sorted((self.should_tail(file_to_check, checkpoint) for file_to_check in glob.glob(self.args.source_pattern)), key=lambda x: x[1] if x else x))
                if self.args.verbose: print 'checkpoint', checkpoint
                if self.args.verbose: print 'to_tail', to_tail
                if self.args.verbose: time.sleep(5)
                file_to_tail, checkpoint = to_tail[0]
                to_tail = to_tail[1:]
                
                #raw_input()
                for offset, record in self.scan(file_to_tail, checkpoint):
                    self.handoff(file_to_tail, checkpoint, record)
                    checkpoint = checkpoint[0], time.time(), offset
                    self.save_checkpoint(self.checkpoint_filename, checkpoint)
            except KeyboardInterrupt:
                return
            except:
                import traceback
                traceback.print_exc()
            finally:
                self.save_checkpoint(self.checkpoint_filename, checkpoint)
            time.sleep(5)

    def scan(self, filename, (sig, st_mtime,  offset)):
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



    @classmethod
    def add_args(cls, parser):
        parser.add_argument('source_pattern',   help='source pattern is the glob path to a file to be tailed plus its rotated versions')
        parser.add_argument('--verbose',  action='store_true',  default=False, help='prints a lot crap, default is: %s' % False )
        parser.add_argument('--dryrun',  action='store_true',  default=False, help='prints a lot crap and no hand-off, default is: %s' % False )
        parser.add_argument('--backfill',  action='store_true',  default=True, help='backfill with rolled logs, default is: %s' % False )    
        return parser





