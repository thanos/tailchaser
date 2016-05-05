# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
#
# $Id$
#
# Developer: Thanos Vassilakis


import logging
import sys

log = logging.getLogger(__name__)


def producer(func):
    def produce_func(s):
        for item in s:
            yield func(item)

    return produce_func


def consumer(func):
    def start(*args, **kwargs):
        c = func(*args, **kwargs)
        c.next()
        return c

    return start


class Reader(object):
    def __init__(self, *args, **kwargs):
        self.source = args[0]

    def process(self, receiver):
        receiver.next()
        while True:
            buff = self.source.read(1000)
            if buff:
                receiver.send(buff)


class CollectLines(object):
    def __init__(self, *args, **kwargs):
        self.count = 0

    def process(self, receiver):
        receiver.next()
        while True:
            buff = (yield)
            if buff:
                while True:
                    indx = buff.find('\n')
                    if indx == -1:
                        break
                    self.count += 1
                    receiver.send("%08d: " % self.count)
                    receiver.send(buff[:indx + 1])
                    buff = buff[indx + 1:]
                receiver.send(buff)


class Printer(object):
    def __init__(self, *args, **kwargs):
        pass

    def process(self):
        while True:
            buff = (yield)
            sys.stdout.write(buff)


if __name__ == '__main__':
    import StringIO

    f = StringIO.StringIO()
    Reader(open(__file__)).process(CollectLines().process(Printer().process()))
