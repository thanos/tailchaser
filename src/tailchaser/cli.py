"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mtailchaser` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``tailchaser.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``tailchaser.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""
import argparse
import logging
import sys

from tailer import Tailer

log = logging.getLogger(__name__)


def main(argv=sys.argv, consumer=None):
    """

    Args:
        argv (list): List of arguments
        consumer: an optional consumer

    Returns:
        int: A return code

    Does stuff.
    """
    # print argv
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('file-pattern',
                        help='file pattern to tail, such as /var/log/access.*')
    parser.add_argument('--only-backfill', action='store_true', default=Tailer.ONLY_BACKFILL,
                        help='dont\'t tail, default: %s' % Tailer.ONLY_BACKFILL)
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
    args = vars(parser.parse_args(argv[1:]))
    file_pattern = args.pop('file-pattern')
    reading_from = args.pop('reading_from')
    logging_level = getattr(logging, args.pop('logging'))

    if reading_from == 'win':
        args['read_pause'] = 1
        args['read_period'] = 1
    else:
        args['read_pause'] = 0
        args['read_period'] = 0

    # print file_pattern, args, logging_level
    # raw_input()
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging_level)
    Tailer(**args).run(file_pattern, consumer)
    return 0
