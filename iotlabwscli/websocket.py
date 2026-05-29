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

import asyncio
import sys
from collections import OrderedDict
from typing import Any, NamedTuple

import websockets
import websockets.exceptions
from iotlabcli.parser import common as common_parser


class Session(NamedTuple):
    """Websocket session credentials."""

    host: str
    exp_id: int
    user: str
    token: str


class Connection(NamedTuple):
    """Node connection parameters."""

    session: Session
    site: str
    node: str


class WebsocketClient:
    # pylint:disable=too-few-public-methods
    """Class that connects to a websocket server while listening to stdin."""

    def __init__(self, connection: Connection, con_type: str) -> None:
        self.connection = connection
        self.websocket: Any = None
        self.url = (
            f"wss://{connection.session.host}:443/ws/{connection.site}/"
            f"{connection.session.exp_id}/{connection.node}/{con_type}"
        )

    async def run(self) -> None:
        """Connect to websocket and listen for incoming messages."""
        node_site = f"{self.connection.node}.{self.connection.site}"
        try:
            async with websockets.connect(
                self.url,
                subprotocols=[
                    self.connection.session.user,
                    "token",
                    self.connection.session.token,
                ],
            ) as self.websocket:
                print(f"Connected to {node_site}")
                await self._listen()
        except (websockets.exceptions.WebSocketException, OSError) as exc:
            print(f"Connection to {node_site} failed: {exc}")
        finally:
            self.websocket = None

    async def _listen(self) -> None:
        """Listen to all incoming data from websocket connection."""
        data = ""
        while True:
            try:
                recv = await self.websocket.recv()
            except websockets.exceptions.ConnectionClosed as exc:
                print(
                    f"Disconnected from {self.connection.node}."
                    f"{self.connection.site}: {exc}"
                )
                await asyncio.sleep(0.1)
                return
            if isinstance(recv, bytes):
                try:
                    data += recv.decode("utf-8")
                except UnicodeDecodeError:
                    continue
            else:
                data += recv
            lines = data.splitlines(True)
            data = ""
            for line in lines:
                if line[-1] == "\n":
                    line = line[:-1]
                    sys.stdout.write(
                        f"{self.connection.node}.{self.connection.site}: "
                        f"{line}\n"
                    )
                    sys.stdout.flush()
                else:
                    data = line  # last incomplete line


class WebsocketsSerialAggregator:  # pylint:disable=too-few-public-methods
    """Class that aggregates all websocket connections to stdin/out."""

    def __init__(self, connections: list[Connection]) -> None:
        self.clients: dict[str, WebsocketClient] = {
            f"{connection.node}.{connection.site}": WebsocketClient(
                connection, con_type="serial/raw"
            )
            for connection in connections
        }
        self._loop: asyncio.AbstractEventLoop | None = None

    @staticmethod
    async def _send_client(client: WebsocketClient, message: str) -> None:
        if client.websocket is None:
            # don't send to a disconnected client
            return
        msg = message + "\n"
        await client.websocket.send(msg.encode())

    async def _send_all_clients(self, message: str) -> None:
        await asyncio.gather(
            *[self._send_client(c, message) for c in self.clients.values()]
        )

    async def _send_clients(
        self, nodes: list[str] | None, message: str
    ) -> None:
        if nodes is None:
            await self._send_all_clients(message)
        else:
            for node in nodes:
                node_str = ".".join(node.split(".")[:2])
                if node_str in self.clients:
                    await self._send_client(self.clients[node_str], message)

    def _listen_stdin(self) -> None:
        def _handle_stdin() -> None:
            message = sys.stdin.readline().strip()
            nodes, message = self.extract_nodes_and_message(message)
            if (None, "") != (nodes, message):  # skip empty message
                assert self._loop is not None
                self._loop.create_task(self._send_clients(nodes, message))

        assert self._loop is not None
        self._loop.add_reader(sys.stdin.fileno(), _handle_stdin)

    @staticmethod
    def extract_nodes_and_message(
        line: str,
    ) -> tuple[list[str] | None, str]:
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
            nodes_str, message = line.split(";")
            if nodes_str == "-":
                return None, message

            site, archi, list_str = nodes_str.split(",")

            # normalize archi
            archi = archi.lower()

            # get nodes list
            nodes = common_parser.nodes_list_from_info(site, archi, list_str)

            return nodes, message
        except (IndexError, ValueError):
            return None, line

    async def run(self) -> None:
        """Starts the clients serial aggregation workflow."""
        self._loop = asyncio.get_running_loop()
        self._listen_stdin()
        await asyncio.gather(
            *[client.run() for client in self.clients.values()]
        )
        self._loop.remove_reader(sys.stdin.fileno())


def _group_nodes(nodes: list[str]) -> OrderedDict[str, list[str]]:
    """Returns a dict with sites as keys and list of nodes as values.

    >>> list(_group_nodes(['m3-1.saclay.iot-lab.info']).items())
    [('saclay', ['m3-1'])]
    >>> list(_group_nodes(['nrf52dk-7.saclay']).items())
    [('saclay', ['nrf52dk-7'])]
    >>> n = ['m3-1.saclay.iot-lab.info', 'nrf52dk-7.saclay']
    >>> list(_group_nodes(n).items())
    [('saclay', ['m3-1', 'nrf52dk-7'])]
    >>> list(_group_nodes(['m3-1.saclay', 'm3-1.grenoble']).items())
    [('grenoble', ['m3-1']), ('saclay', ['m3-1'])]
    >>> list(_group_nodes(['m3-1.saclay', 'm3-1']).items())
    [('saclay', ['m3-1'])]
    >>> list(_group_nodes(['invalid']).items())
    []
    """
    nodes_grouped: dict[str, list[str]] = {}
    for node in nodes:
        node_split = node.split(".")
        if len(node_split) < 2:
            continue
        node_name, site = node_split[:2]
        if site not in nodes_grouped:
            nodes_grouped.update({site: [node_name]})
        else:
            nodes_grouped[site].append(node_name)

    return OrderedDict(sorted(nodes_grouped.items(), key=lambda t: t[0]))


def start(session: Session, nodes: list[str]) -> int:
    """Start a websocket session on nodes."""
    try:
        _nodes_grouped = _group_nodes(nodes)
        connections = [
            Connection(session, site, node)
            for site, _nodes in _nodes_grouped.items()
            for node in _nodes
        ]

        aggregator = WebsocketsSerialAggregator(connections)
        asyncio.run(aggregator.run())
    except KeyboardInterrupt:
        print("Exiting")
    return 0
