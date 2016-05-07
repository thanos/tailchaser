import re
import sys


class Node(object):
    def __init__(self, config, *args, **kwargs):
        self.config = self.configure(config)

    def configure(self, config):
        return config

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
    def __init__(self, config, *args, **kwargs):
        super(Reader, self).__init__(config, *args, **kwargs)
        self.source = self.config['SOURCE']

    def run(self, receiver):
        while True:
            something = self.source.read(10000)
            self.send(self.process(something), receiver)


class CollectLines(Node):
    def __init__(self, config, *args, **kwargs):
        super(CollectLines, self).__init__(config, *args, **kwargs)
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
                    self.send(buff[:indx + 1], receiver)
                    buff = buff[indx + 1:]
                self.send(buff, receiver)


class CollectRecords(Node):
    def __init__(self, config, *args, **kwargs):
        super(CollectRecords, self).__init__(config, *args, **kwargs)
        self.count = 0

    def run(self, receiver):
        buff = ''
        first_record = True
        e = 0
        s = 0
        while True:
            buff += (yield)
            if buff:
                while True:
                    match = self.config['SOR_RE'].search(buff, e - s)
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

    def send(self, something, receiver):
        self.count += 1
        super(CollectRecords, self).send("%000d->" % self.count, receiver)
        super(CollectRecords, self).send(something, receiver)


class Printer(Node):
    def send(self, something, receiver):
        if something:
            sys.stdout.write(something)


class System(object):
    def wire_up(self, *nodes, **config):
        if nodes:
            return nodes[0](config).receive(self.wire_up(*nodes[1:], **config))


if __name__ == '__main__':
    System().wire_up(Reader, CollectRecords, Printer,
                     SOURCE=open('/var/log/install.log', 'rb'),
                     SOR_RE=re.compile(r'\w+\s+\d+\s+\d\d:\d\d:\d\d'))
