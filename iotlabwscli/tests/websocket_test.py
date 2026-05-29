# -*- coding: utf-8 -*-

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

"""Tests for iotlabwscli.websocket module."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import websockets.exceptions
from websockets.exceptions import ConnectionClosedOK

from iotlabwscli.websocket import (
    Connection,
    Session,
    WebsocketClient,
    WebsocketsSerialAggregator,
    start,
)

SESSION = Session("host.example.com", 1, "user", "token")
CONNECTION = Connection(SESSION, "saclay", "m3-1")


# pylint: disable=too-many-public-methods,protected-access
class TestWebsocketClient(unittest.IsolatedAsyncioTestCase):
    """Tests for WebsocketClient."""

    def setUp(self):
        self.client = WebsocketClient(CONNECTION, "serial/raw")

    def test_init(self):
        """Verify URL construction and initial websocket state."""
        assert self.client.websocket is None
        assert self.client.url == (
            "wss://host.example.com:443/ws/saclay/1/m3-1/serial/raw"
        )

    async def test_run_os_error(self):
        """OSError during connect is caught; websocket stays None."""
        with patch(
            "websockets.connect", side_effect=OSError("Connection refused")
        ):
            await self.client.run()
        assert self.client.websocket is None

    async def test_run_websocket_exception(self):
        """WebSocketException during connect is handled cleanly."""
        with patch(
            "websockets.connect",
            side_effect=websockets.exceptions.WebSocketException(),
        ):
            await self.client.run()
        assert self.client.websocket is None

    async def test_run_success_then_disconnect(self):
        """Successful connection receives data then closes cleanly."""
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = [
            b"hello\n",
            ConnectionClosedOK(rcvd=None, sent=None),
        ]
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_ws
        with patch("websockets.connect", return_value=mock_ctx):
            with patch("sys.stdout"):
                await self.client.run()
        assert self.client.websocket is None

    async def test_listen_unicode_error(self):
        """Bytes that cannot be decoded as UTF-8 are skipped."""
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = [
            b"\xff\xfe",
            ConnectionClosedOK(rcvd=None, sent=None),
        ]
        self.client.websocket = mock_ws
        await self.client._listen()

    async def test_listen_text_frame(self):
        """String (text frame) messages are handled directly."""
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = [
            "text line\n",
            ConnectionClosedOK(rcvd=None, sent=None),
        ]
        self.client.websocket = mock_ws
        with patch("sys.stdout"):
            await self.client._listen()

    async def test_listen_incomplete_line(self):
        """Partial lines are buffered until a newline arrives."""
        mock_ws = AsyncMock()
        mock_ws.recv.side_effect = [
            b"part",
            b"ial\n",
            ConnectionClosedOK(rcvd=None, sent=None),
        ]
        self.client.websocket = mock_ws
        with patch("sys.stdout"):
            await self.client._listen()


# pylint: disable=too-many-public-methods,protected-access
class TestWebsocketsSerialAggregator(unittest.IsolatedAsyncioTestCase):
    """Tests for WebsocketsSerialAggregator."""

    def setUp(self):
        self.aggregator = WebsocketsSerialAggregator([CONNECTION])

    def test_init(self):
        """Clients dict is keyed by 'node.site'."""
        assert "m3-1.saclay" in self.aggregator.clients

    async def test_send_client_disconnected(self):
        """_send_client is a no-op when the websocket is None."""
        client = MagicMock()
        client.websocket = None
        await WebsocketsSerialAggregator._send_client(client, "msg")

    async def test_send_client_connected(self):
        """_send_client sends message bytes with a trailing newline."""
        client = MagicMock()
        client.websocket = AsyncMock()
        await WebsocketsSerialAggregator._send_client(client, "msg")
        client.websocket.send.assert_called_once_with(b"msg\n")

    async def test_send_all_clients(self):
        """_send_all_clients broadcasts to every client."""
        for c in self.aggregator.clients.values():
            c.websocket = AsyncMock()
        await self.aggregator._send_all_clients("hello")
        for c in self.aggregator.clients.values():
            c.websocket.send.assert_called_once_with(b"hello\n")

    async def test_send_clients_to_all(self):
        """_send_clients with nodes=None sends to all clients."""
        for c in self.aggregator.clients.values():
            c.websocket = AsyncMock()
        await self.aggregator._send_clients(None, "hi")
        for c in self.aggregator.clients.values():
            c.websocket.send.assert_called_once()

    async def test_send_clients_to_specific(self):
        """_send_clients routes a message to the matching node only."""
        for c in self.aggregator.clients.values():
            c.websocket = AsyncMock()
        await self.aggregator._send_clients(["m3-1.saclay.iot-lab.info"], "hi")
        self.aggregator.clients[
            "m3-1.saclay"
        ].websocket.send.assert_called_once()

    async def test_send_clients_unknown_node(self):
        """_send_clients silently ignores unrecognised node names."""
        for c in self.aggregator.clients.values():
            c.websocket = AsyncMock()
        await self.aggregator._send_clients(["m3-99.unknown"], "hi")
        for c in self.aggregator.clients.values():
            c.websocket.send.assert_not_called()

    def test_listen_stdin_empty_message(self):
        """Empty (whitespace-only) stdin lines do not schedule a send."""
        self.aggregator._loop = MagicMock()
        self.aggregator._listen_stdin()
        callback = self.aggregator._loop.add_reader.call_args[0][1]
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.readline.return_value = "\n"
            callback()
        self.aggregator._loop.create_task.assert_not_called()

    def test_listen_stdin_send_message(self):
        """Non-empty stdin lines schedule a _send_clients task."""
        self.aggregator._loop = MagicMock()
        with patch.object(
            self.aggregator, "_send_clients", new_callable=AsyncMock
        ):
            self.aggregator._listen_stdin()
            callback = self.aggregator._loop.add_reader.call_args[0][1]
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.readline.return_value = "hello\n"
                callback()
            # Close the unawaited coroutine to avoid RuntimeWarning
            self.aggregator._loop.create_task.call_args[0][0].close()
        self.aggregator._loop.create_task.assert_called_once()

    async def test_run(self):
        """run() registers stdin reader and removes it on exit."""
        for c in self.aggregator.clients.values():
            c.run = AsyncMock()
        loop = asyncio.get_running_loop()
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.fileno.return_value = 0
            with patch.object(loop, "add_reader") as mock_add:
                with patch.object(loop, "remove_reader") as mock_remove:
                    await self.aggregator.run()
        mock_add.assert_called_once()
        mock_remove.assert_called_once_with(0)


class TestStart(unittest.TestCase):
    """Tests for the module-level start() function."""

    def test_start_runs_aggregator(self):
        """start() wraps aggregator.run() in asyncio.run and returns 0."""
        nodes = ["m3-1.saclay.iot-lab.info"]
        with patch("iotlabwscli.websocket.asyncio.run") as mock_run:
            result = start(SESSION, nodes)
        # Close the unawaited coroutine to avoid RuntimeWarning
        mock_run.call_args[0][0].close()
        assert result == 0
        mock_run.assert_called_once()

    def test_start_keyboard_interrupt(self):
        """KeyboardInterrupt is caught; start() still returns 0."""
        nodes = ["m3-1.saclay.iot-lab.info"]
        with patch(
            "iotlabwscli.websocket.asyncio.run", side_effect=KeyboardInterrupt
        ) as mock_run:
            with patch("builtins.print") as mock_print:
                result = start(SESSION, nodes)
        # Close the unawaited coroutine to avoid RuntimeWarning
        mock_run.call_args[0][0].close()
        assert result == 0
        mock_print.assert_called_with("Exiting")
