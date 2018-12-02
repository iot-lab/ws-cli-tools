# -*- coding:utf-8 -*-
"""iotlabwscli client for Websocket cli."""

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

try:
    from urllib.parse import urlparse
except ImportError:  # Python 2
    from urlparse import urlparse

import tornado
from tornado import gen

from .websocket import WebsocketClient


def _parse_node(node_fqdn):
    """Return the node name and site from the node fqdn.

    >>> _parse_node('m3-1.saclay.iot-lab.info')
    ['m3-1', 'saclay']
    >>> _parse_node('nrf52dk-7.saclay')
    ['nrf52dk-7', 'saclay']
    >>> _parse_node('invalid')
    Traceback (most recent call last):
    ...
    ValueError: Invalid node name 'invalid'...
    """
    node_split = node_fqdn.split('.')

    if len(node_split) < 2:
        raise ValueError("Invalid node name '{}'. Node name should use the "
                         "following scheme: <hostname>.<site>"
                         .format(node_fqdn))
    return node_split[:2]


def start(url, node, exp_id, user, token, con_type="serial"):
    """Start a websocket session on nodes."""
    try:
        node, site = _parse_node(node)
        host = urlparse(url).netloc

        url = "wss://{}:443/ws/{}/{}/{}/{}".format(
            host, site, exp_id, node, con_type)
        ws_client = WebsocketClient(url, user, token)
        ws_client.run()
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print("Exiting")
    finally:
        tornado.ioloop.IOLoop.instance().stop()
    return 0
