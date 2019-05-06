# -*- coding:utf-8 -*-
"""iotlabwscli websocket."""

# This file is a part of IoT-LAB ws-cli-tools
# Copyright (C) 2015 INRIA (Contact: admin@iot-lab.info)
# Contributor(s) : see AUTHORS file
#
# This software is governed by the CeCILL license under French law
# and abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL
# license as circulated by CEA, CNRS and INRIA at the following URL
# http://www.cecill.info.
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL license and that you accept its terms.

from __future__ import print_function

import sys

from collections import OrderedDict, namedtuple

import tornado
from tornado import gen
from tornado.websocket import websocket_connect
from tornado.httpclient import HTTPClientError

from iotlabcli.parser import common as common_parser


Session = namedtuple('Session', ['host', 'exp_id', 'user', 'token'])
Connection = namedtuple('Connection', ['session', 'site', 'node'])


class WebsocketClient:
    # pylint:disable=too-few-public-methods
    """Class that connects to a websocket server while listening to stdin."""

    def __init__(self, connection, con_type):
        self.connection = connection
        self.websocket = None
        self.url = ("wss://{0.session.host}:443/ws/"
                    "{0.site}/{0.session.exp_id}/{0.node}/{1}"
                    .format(connection, con_type))

    @gen.coroutine
    def connect(self):
        """Initiate a websocket connection of the client."""
        try:
            self.websocket = yield websocket_connect(
                self.url, subprotocols=[self.connection.session.user,
                                        'token',
                                        self.connection.session.token])
        except HTTPClientError as exc:
            print("Connection to {0.node}.{0.site} failed: {1}"
                  .format(self.connection, exc))
            self.websocket = None
            return
        print("Connected to {0.node}.{0.site}"
              .format(self.connection))

    @gen.coroutine
    def listen(self):
        """Listen to all incoming data from websocket connection."""
        data = ''
        while True:
            recv = yield self.websocket.read_message()
            if recv is None:
                print("Disconnected from {0.node}.{0.site}: {1}"
                      .format(self.connection, self.websocket.close_reason))
                # Let some time to the loop to catch any pending exception
                yield gen.sleep(0.1)
                self.websocket = None
                return
            try:
                data += recv.decode('utf-8')
            except UnicodeDecodeError:
                continue
            lines = data.splitlines(True)
            data = ''
            for line in lines:
                if line[-1] == '\n':
                    line = line[:-1]
                    sys.stdout.write('{0.node}.{0.site}: '
                                     .format(self.connection))
                    sys.stdout.write(line)
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                else:
                    data = line  # last incomplete line


class WebsocketsSerialAggregator:  # pylint:disable=too-few-public-methods
    """Class that aggregates all websocket connections to stdin/out."""

    def __init__(self, connections):
        self.clients = {
            '{0.node}.{0.site}'.format(connection): WebsocketClient(
                connection, con_type='serial/raw')
            for connection in connections
        }

    @staticmethod
    def _send_client(client, message):
        if client.websocket is None:
            # don't send to a disconnected client
            return
        msg = message + '\n'
        client.websocket.write_message(msg.encode(), binary=True)

    def _send_all_clients(self, message):
        for client in self.clients.values():
            self._send_client(client, message)

    def _send_clients(self, nodes, message):
        if nodes is None:
            self._send_all_clients(message)
        else:
            for node in nodes:
                node_str = '.'.join(node.split('.')[:2])
                if node_str in self.clients:
                    self._send_client(self.clients[node_str], message)

    def _listen_stdin(self):
        def _handle_stdin(file_descriptor, handler):
            # pylint:disable=unused-argument
            message = file_descriptor.readline().strip()
            try:
                nodes, message = self.extract_nodes_and_message(message)
                if (None, '') != (nodes, message):  # skip empty message
                    self._send_clients(nodes, message)
            except UnicodeDecodeError:
                pass
        ioloop = tornado.ioloop.IOLoop.current()
        ioloop.add_handler(sys.stdin, _handle_stdin,
                           tornado.ioloop.IOLoop.READ)

    @staticmethod
    def extract_nodes_and_message(line):
        """
        >>> WebsocketsSerialAggregator.extract_nodes_and_message('')
        (None, '')

        >>> WebsocketsSerialAggregator.extract_nodes_and_message(' ')
        (None, ' ')

        >>> WebsocketsSerialAggregator.extract_nodes_and_message('message')
        (None, 'message')

        >>> WebsocketsSerialAggregator.extract_nodes_and_message('-;message')
        (None, 'message')

        >>> WebsocketsSerialAggregator.extract_nodes_and_message(
        ...     'my_message_csv;msg')
        (None, 'my_message_csv;msg')

        >>> WebsocketsSerialAggregator.extract_nodes_and_message(
        ...      'saclay,M3,1;message')
        (['m3-1.saclay.iot-lab.info'], 'message')

        >>> WebsocketsSerialAggregator.extract_nodes_and_message(
        ...     'saclay,m3,1-3+5;message')
        ... # doctest: +NORMALIZE_WHITESPACE
        (['m3-1.saclay.iot-lab.info', 'm3-2.saclay.iot-lab.info', \
          'm3-3.saclay.iot-lab.info', 'm3-5.saclay.iot-lab.info'], 'message')
        """
        try:
            nodes_str, message = line.split(';')
            if nodes_str == '-':
                return None, message

            site, archi, list_str = nodes_str.split(',')

            # normalize archi
            archi = archi.lower()

            # get nodes list
            nodes = common_parser.nodes_list_from_info(site, archi, list_str)

            return nodes, message
        except (IndexError, ValueError):
            return None, line

    @gen.coroutine
    def run(self):
        """Starts the clients serial aggregation workflow."""
        # Connect all clients
        yield gen.multi([client.connect() for client in self.clients.values()])

        # Start stdin listener
        self._listen_stdin()

        # Start listening all opened client connections
        yield gen.multi([client.listen() for client in self.clients.values()
                         if client.websocket is not None])

        tornado.ioloop.IOLoop.instance().stop()


def _group_nodes(nodes):
    """Returns a dict with sites as keys and list of nodes as values.

    >>> _group_nodes(['m3-1.saclay.iot-lab.info'])
    OrderedDict([('saclay', ['m3-1'])])
    >>> _group_nodes(['nrf52dk-7.saclay'])
    OrderedDict([('saclay', ['nrf52dk-7'])])
    >>> _group_nodes(['m3-1.saclay.iot-lab.info', 'nrf52dk-7.saclay'])
    OrderedDict([('saclay', ['m3-1', 'nrf52dk-7'])])
    >>> _group_nodes(['m3-1.saclay', 'm3-1.grenoble'])
    OrderedDict([('grenoble', ['m3-1']), ('saclay', ['m3-1'])])
    >>> _group_nodes(['m3-1.saclay', 'm3-1'])
    OrderedDict([('saclay', ['m3-1'])])
    >>> _group_nodes(['invalid'])
    OrderedDict()
    """
    nodes_grouped = dict()
    for node in nodes:
        node_split = node.split('.')
        if len(node_split) < 2:
            continue
        node_name, site = node_split[:2]
        if site not in nodes_grouped:
            nodes_grouped.update({site: [node_name]})
        else:
            nodes_grouped[site].append(node_name)

    return OrderedDict(sorted(nodes_grouped.items(), key=lambda t: t[0]))


def start(session, nodes):
    """Start a websocket session on nodes."""
    try:
        _nodes_grouped = _group_nodes(nodes)
        connections = [Connection(session, site, node)
                       for site, _nodes in _nodes_grouped.items()
                       for node in _nodes]

        aggregator = WebsocketsSerialAggregator(connections)
        aggregator.run()
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print("Exiting")
    finally:
        tornado.ioloop.IOLoop.instance().stop()
    return 0
