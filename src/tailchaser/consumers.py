"""
Module that contains the the chaser (collector) classes.

"""


class StdOut(object):
    def __init__(self, args):
        pass

    def process(self, checkpoint, record):
        print checkpoint, record
