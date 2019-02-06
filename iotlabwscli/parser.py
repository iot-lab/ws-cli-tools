# -*- coding:utf-8 -*-
"""iotlabwscli parser for Websocket cli."""

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


import sys
import argparse
import json
from collections import defaultdict

try:
    from urllib.parse import urlparse
except ImportError:  # Python 2
    from urlparse import urlparse

import tornado
import tornado.httpclient

from iotlabcli import auth
from iotlabcli import helpers
from iotlabcli import rest
from iotlabcli.parser import common
from iotlabcli.parser.common import _get_experiment_nodes_list

import iotlabwscli
from iotlabwscli.websocket import start, Session


WS_MAX_CONNECTIONS = 10


def parse_options():
    """Parse command line option."""
    parser = argparse.ArgumentParser()
    common.add_auth_arguments(parser, False)
    common.add_output_formatter(parser)
    # nodes list or exclude list
    common.add_nodes_selection_list(parser)
    parser.add_argument('-v', '--version', action='version',
                        version=iotlabwscli.__version__)
    common.add_expid_arg(parser)
    parser.add_argument('--verbose', action='store_true',
                        help='Set verbose output')
    return parser


def _check_nodes_list(nodes_list):
    node_dict = defaultdict(list)

    for node in nodes_list:
        _node, _site = node.split('.')[:2]
        node_dict[_site].append(_node)

    ret = 0
    for site, nodes in node_dict.items():
        if len(nodes) > WS_MAX_CONNECTIONS:
            print("Too much nodes requested ({}) for site {}, {} are "
                  "allowed at maximum for each site.".format(
                      len(nodes), site, WS_MAX_CONNECTIONS))
            ret += 1
    return ret


def parse_and_run(opts):
    """Parse namespace 'opts' object and execute M3 fw update action."""
    user, passwd = auth.get_user_credentials(opts.username, opts.password)
    api = rest.Api(user, passwd)
    exp_id = helpers.get_current_experiment(api, opts.experiment_id)

    # Fetch token from new API
    host = urlparse(api.url).netloc
    api_url = 'https://{}/api/experiments/{}/token'.format(host, exp_id)
    request_kwargs = {'auth_username': user, 'auth_password': passwd}
    request = tornado.httpclient.HTTPRequest(api_url, **request_kwargs)
    request.headers["Content-Type"] = "application/json"
    client = tornado.httpclient.HTTPClient()

    try:
        token_response = client.fetch(request).buffer.read()
    except tornado.httpclient.HTTPClientError as exc:
        # pylint:disable=superfluous-parens
        print("Failed to fetch token from API: {}".format(exc))
        return 1

    token = json.loads(token_response.decode())['token']
    nodes = common.list_nodes(api, exp_id, opts.nodes_list,
                              opts.exclude_nodes_list)

    # Only if nodes_list or exclude_nodes_list is not specify (nodes = [])
    if not nodes:
        nodes = _get_experiment_nodes_list(api, exp_id)

    # Drop A8 nodes
    nodes = ["{}".format(node) for node in nodes if not node.startswith('a8')]

    if not nodes:
        return 1

    if _check_nodes_list(nodes) > 0:
        return 1

    return start(Session(host, exp_id, user, token), nodes)


def main(args=None):
    """Websocket client cli parser."""
    args = args or sys.argv[1:]  # required for easy testing.
    parser = parse_options()
    common.main_cli(parse_and_run, parser, args)
