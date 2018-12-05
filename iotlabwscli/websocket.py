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

try:
    from urllib.parse import urlparse
except ImportError:  # Python 2
    from urlparse import urlparse

import tornado
from tornado import gen
from tornado.websocket import websocket_connect
from tornado.httpclient import HTTPClientError


Connection = namedtuple('Connection',
                        ['host', 'site', 'exp_id', 'user',
                         'node', 'token', 'con_type'])


class WebsocketClient:
    # pylint:disable=too-few-public-methods
    """Class that connects to a websocket server while listening to stdin."""

    def __init__(self, connection):
        self.connection = connection
        self.websocket = None
        self.url = ("wss://{0.host}:443/ws/{0.site}/{0.exp_id}/"
                    "{0.node}/{0.con_type}".format(connection))

    @gen.coroutine
    def _connect(self):
        try:
            self.websocket = yield websocket_connect(
                self.url, subprotocols=[self.connection.user,
                                        'token', self.connection.token])
        except HTTPClientError as exc:
            print("Websocket connection failed: %s", exc)
            tornado.ioloop.IOLoop.instance().stop()
            return
        print("Websocket connection opened")

    @gen.coroutine
    def _listen_websocket(self):
        while True:
            data = yield self.websocket.read_message()
            if data is None:
                print("Websocket connection closed:",
                      self.websocket.close_reason)
                # Let some time to the loop to catch any pending exception
                yield gen.sleep(0.1)
                tornado.ioloop.IOLoop.instance().stop()
                return
            # Print received data to stdout
            sys.stdout.write(data)
            sys.stdout.flush()

    @gen.coroutine
    def _listen_stdin(self):
        def _handle_stdin(file_descriptor, handler):
            # pylint:disable=unused-argument
            message = file_descriptor.readline().strip()
            try:
                self.websocket.write_message(message.decode() + '\n')
            except UnicodeDecodeError:
                pass
        ioloop = tornado.ioloop.IOLoop.current()
        ioloop.add_handler(sys.stdin, _handle_stdin,
                           tornado.ioloop.IOLoop.READ)

    @gen.coroutine
    def run(self):
        """Connect and listen to the websocket server and listen to stdin."""
        # Wait for connection
        yield self._connect()

        # Start stdin listener as background task
        yield self._listen_stdin()
        # Start websocket listener
        yield self._listen_websocket()


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


def start(url, nodes, exp_id, user, token, con_type="serial"):
    """Start a websocket session on nodes."""
    try:
        web_host = urlparse(url).netloc
        _nodes_grouped = _group_nodes(nodes)

        connection = Connection(web_host, site, exp_id, user,
                                node, token, con_type)

        ws_client = WebsocketClient(connection)
        ws_client.run()
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print("Exiting")
    finally:
        tornado.ioloop.IOLoop.instance().stop()
    return 0
