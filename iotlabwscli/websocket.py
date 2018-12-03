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

import tornado
from tornado import gen
from tornado.websocket import websocket_connect
from tornado.httpclient import HTTPClientError


class WebsocketClient:
    # pylint:disable=too-few-public-methods
    """Class that connects to a websocket server while listening to stdin."""

    def __init__(self, url, user, token):
        self.url = url
        self.token = token
        self.user = user
        self.websocket = None

    @gen.coroutine
    def _connect(self):
        try:
            self.websocket = yield websocket_connect(
                self.url, subprotocols=[self.user, 'token', self.token])
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
