import logging.handlers
import logging,threading
import sys, pprint,os,shutil, time
import argparse

FORMAT = '%(asctime)s %(levelname)s  %(module)s %(process)d %(thread)d %(message)s'
LOGNUM= 1
MAX_LOGS_PER_DIR = max(LOGNUM/10,1)
MAX_LOG_SIZE = 2**20
MSG_SIZE = 100
MAX_LOG_ENTRIES = MAX_LOG_SIZE

def get_args():
    parser = argparse.ArgumentParser(description='tests the various hackathon services',
            prog='loggen',
            usage= '%(prog)s [options] destination_path'
            )
    parser.add_argument('path_head',    help='path to store log files')
    parser.add_argument('--lognum', type=int,  default=LOGNUM, help='number of logfiles to generate: %s' % LOGNUM)
    parser.add_argument('--message_size', type=int,  default=MSG_SIZE, help='message size: %s' % MSG_SIZE)
    parser.add_argument('--max_logs_per_dir', type=int,  default=MAX_LOGS_PER_DIR, help='number of logfiles per directory: %s' % MAX_LOGS_PER_DIR)
    parser.add_argument('--max_log_size', type=int,  default=MAX_LOG_SIZE, help='max log size before you rotate: %s' % MAX_LOG_SIZE)
    parser.add_argument('--max_log_entries', type=int,  default=MAX_LOG_ENTRIES, help='max log entries (0= unlimited) : %s' % MAX_LOG_ENTRIES)
    parser.add_argument('--format',   default=FORMAT, help='flog foromat, default: %s' % FORMAT)
    parser.add_argument('--gen',  action='store_true',  default=False, help='dry runs, default is: %s' % True )
    parser.add_argument('--tail',  action='store_true',  default=False, help='dry runs, default is: %s' % False )
    parser.add_argument('--dryrun',  action='store_true',  default=False, help='dry runs, default is: %s' % False )
    parser.add_argument('--delete',  action='store_true',  default=False, help='deletes all test logs and their directories, default is: %s' % False )
    return parser.parse_args()




if __name__ =='__main__':
    import sys, random
    args = get_args()
    abs_path = os.path.abspath(args.path_head)
    if not os.path.exists(abs_path): os.makedirs(abs_path)
    logger = logging.getLogger()
    log_file = os.path.join(abs_path, "test.log")
    handler = logging.handlers.RotatingFileHandler(log_file,  maxBytes= 400*1024, backupCount=20)
    handler.setFormatter(logging.Formatter(args.format))
    logger.addHandler(handler)
    for i in xrange(10**6):
        logger.error("%d - %s", i+1, "X"* 128)
        time.sleep(random.uniform(.1, 1))