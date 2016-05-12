# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
#
# $Id$
#
# Developer: Thanos Vassilakis
import argparse
import getpass
import logging
import os
import platform
import sys

try:
    import regex
except ImportError:
    import re as regex
import requests


__author__ = 'Thanos Vassilakis'
__version__ = "0.2.6"

log = logging.getLogger(__name__)


class Args(object):
    def __init__(self, *positional, **optional):
        self.positional = positional
        self.optional = optional


class System(object):
    CONFIG_ENDPOINT = None

    def args(self):
        return (
            Args('--config_endpoint',
                 default=self.CONFIG_ENDPOINT,
                 help='overrides default hostname for central, %s. Add port if needed like this: some_host:8000'
                      % self.CONFIG_ENDPOINT),
            Args('--logging', choices=['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'], default='ERROR',
                 help='logging level, default: ERROR')
        )

    def __init__(self, *args, **settings):
        self.config = settings
        self.pid = os.getpid()
        self.host = platform.node()
        self.user = getpass.getuser()

    def configure(self, *nodes):
        self.nodes = nodes
        parser = argparse.ArgumentParser(description=self.__doc__ % __version__,
                                         formatter_class=argparse.RawDescriptionHelpFormatter, )

        for args in self.args():
            parser.add_argument(*args.positional, **args.optional)
        for node in nodes:
            for args in node.args():
                if args:
                    parser.add_argument(*args.positional, **args.optional)

        args = vars(parser.parse_args())
        # self.config = args
        # for node in nodes:
        #     args = node.configure(args)

        if args['config_endpoint']:
            url = args['config_endpoint'] % args
            args.update(requests.get(url, params=self.config_params(args)).json())
        self.config.update(args)
        return self

    def config_params(self, args):
        return dict(
            pid=self.pid,
            where=self.host,
            who=self.user
        )

    def wire_up(self, *nodes):
        if nodes:
            return nodes[0](self).receive(self.wire_up(*nodes[1:]))

    def start(self):
        return self.wire_up(*self.nodes)


class Node(object):
    def __init__(self, system):
        self.system = system
        self.settings = self.configure(self.system.config)

    @classmethod
    def args(cls):
        return ()

    def configure(self, args):
        return args

    def config(self, key):
        return self.settings[key]

    def receive(self, receiver=None):
        if receiver:
            receiver.next()
        return self.run(receiver)

    def run(self, receiver):
        while True:
            something = (yield)
            self.send(self.process(something), receiver)

    def process(self, something):
        return something

    def send(self, something, receiver):
        receiver.send(something)


class Reader(Node):
    def run(self, receiver):
        while True:
            something = self.config('SOURCE').read(10000)
            self.send(self.process(something), receiver)


class CollectLines(Node):
    def __init__(self, system):
        super(CollectLines, self).__init__(system)
        self.count = 0

    def run(self, receiver):
        while True:
            buff = (yield)
            if buff:
                while True:
                    indx = buff.find('\n')
                    if indx == -1:
                        break
                    self.count += 1
                    self.send("%08d: " % self.count, receiver)
                    self.send(buff[:indx + 1], receiver)
                    buff = buff[indx + 1:]
                self.send("%08d: " % self.count, receiver)
                self.send(buff, receiver)


class CollectRecords(Node):
    count = 0

    def configure(self, config):
        config['start_of_record_re'] = regex.compile(config['record_seperator_regex']) if config[
            'record_seperator_regex'] else None
        return config

    @classmethod
    def args(cls):
        return (
            Args('--start-of-record-re', default=None,
                 help='use this regex expresion to define the start of a record, default: None'),
        )

    def run(self, receiver):
        buff = ''
        first_record = True
        e = 0
        s = 0
        while True:
            buff += (yield)
            if buff:
                while True:
                    match = self.config('start_of_record_re').search(buff, e - s)
                    self.count += 1
                    if not match:
                        break
                    s, e = match.span(0)
                    if first_record:
                        first_record = False
                        continue
                    self.send(buff[:s], receiver)
                    buff = buff[s:]
                    if not buff:
                        break
        self.send(buff, receiver)


class Printer(Node):
    def send(self, something, receiver):
        if something:
            sys.stdout.write(something)


if __name__ == '__main__':
    System(SOURCE=open('/var/log/install.log', 'rb'),
           start_of_record_re=regex.compile(r'\w+\s+\d+\s+\d\d:\d\d:\d\d')
           ).configure(Reader, CollectRecords, Printer).run()
