import argparse
import logging
import logging.handlers
import os
import random
import tempfile
import time

FORMAT = '%(asctime)s %(levelname)s  %(module)s %(process)d %(thread)d %(message)s'
LOGNUM = 1
MAX_LOGS_PER_DIR = max(LOGNUM / 10, 1)
MAX_LOG_SIZE = 2 ** 20
MSG_SIZE = 100
MAX_LOG_ENTRIES = MAX_LOG_SIZE


def get_args():
    parser = argparse.ArgumentParser(
        description='tests the various hackathon services',
        prog='loggen',
        usage='%(prog)s [options] destination_path'
    )
    parser.add_argument('path_head', help='path to store log files')
    parser.add_argument('--lognum', type=int, default=LOGNUM, help='number of logfiles to generate: %s' % LOGNUM)
    parser.add_argument('--message_size', type=int, default=MSG_SIZE, help='message size: %s' % MSG_SIZE)
    parser.add_argument('--max_logs_per_dir', type=int, default=MAX_LOGS_PER_DIR,
                        help='number of logfiles per directory: %s' % MAX_LOGS_PER_DIR)
    parser.add_argument('--max_log_size', type=int, default=MAX_LOG_SIZE,
                        help='max log size before you rotate: %s' % MAX_LOG_SIZE)
    parser.add_argument('--max_log_entries', type=int, default=MAX_LOG_ENTRIES,
                        help='max log entries (0= unlimited) : %s' % MAX_LOG_ENTRIES)
    parser.add_argument('--format', default=FORMAT, help='flog foromat, default: %s' % FORMAT)
    parser.add_argument('--gen', action='store_true', default=False,
                        help='dry runs, default is: %s' % True)
    parser.add_argument('--tail', action='store_true', default=False,
                        help='dry runs, default is: %s' % False)
    parser.add_argument('--dryrun', action='store_true', default=False,
                        help='dry runs, default is: %s' % False)
    parser.add_argument('--delete', action='store_true', default=False,
                        help='deletes all test logs and their directories, default is: %s' % False)
    return parser.parse_args()


def generate_logfiles(log_file_name, record_number=1024, max_log_size=10*1024, backup_count=20, write_delay=.1,
                      tmp_dir=True):
    abs_file_name = os.path.abspath(log_file_name)
    abs_path, log_file_name = os.path.split(abs_file_name)
    if tmp_dir:
        abs_path = tempfile.mkdtemp(prefix='tailchaser')
        abs_file_name = os.path.join(abs_path, log_file_name)
    print 'abs_file_name', abs_file_name
    if not os.path.exists(abs_path):
        os.makedirs(abs_path)

    logger = logging.getLogger()
    handler = logging.handlers.RotatingFileHandler(abs_file_name, maxBytes=max_log_size, backupCount=backup_count)
    handler.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(handler)
    count = 0
    while count < record_number:
        count += 1
        logger.error("%d - %s", count, "X" * 20)
        time.sleep(random.uniform(0, write_delay))


if __name__ == '__main__':
    import sys

    generate_logfiles(sys.argv[1])
