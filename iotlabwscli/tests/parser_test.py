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

"""Tests for iotlabwscli.parser module."""

import json
from mock import Mock, patch

import tornado.httpclient

import iotlabwscli.parser
from iotlabwscli.parser import urlparse
from iotlabwscli.websocket import Session

from .iotlabwscli_mock import MainMock, ResponseBuffer

# pylint: disable=too-many-public-methods
# pylint: disable=too-few-public-methods


@patch('iotlabwscli.parser.start')
@patch('iotlabcli.parser.common.list_nodes')
@patch('tornado.httpclient.HTTPClient.fetch')
class TestParser(MainMock):
    """Test websocket cli main parser."""

    _nodes = ['m3-1.saclay.iot-lab.info', 'm3-2.saclay.iot-lab.info']

    def test_main_start(self, fetch, list_nodes, start):
        """Run the parser.main."""
        start.return_value = 0
        expected_json = json.dumps({"token": "token"})
        fetch.return_value = ResponseBuffer(expected_json.encode())

        args = ['-l', 'saclay,m3,1']
        list_nodes.return_value = [self._nodes[0]]
        iotlabwscli.parser.main(args)
        list_nodes.assert_called_with(self.api, 123, [[self._nodes[0]]], None)
        expected_session = Session(urlparse(self.api.url).netloc, 123,
                                   'username', 'token')
        start.assert_called_with(expected_session, [self._nodes[0]])

    def test_main_start_empty(self, fetch, list_nodes, start):
        """Run the parser.main."""

        start.return_value = 0
        list_nodes.return_value = []
        expected_json = json.dumps({"token": "token"})
        fetch.return_value = ResponseBuffer(expected_json.encode())

        exp_info_res = {"items": [{"network_address": node}
                                  for node in self._nodes]}
        with patch.object(self.api, 'get_experiment_info',
                          Mock(return_value=exp_info_res)):
            iotlabwscli.parser.main([])
            list_nodes.assert_called_with(self.api, 123, None, None)
            expected_session = Session(urlparse(self.api.url).netloc, 123,
                                       'username', 'token')
            start.assert_called_with(expected_session, self._nodes)

    def test_main_start_no_node(self, fetch, list_nodes, start):
        """Run the parser.main."""

        start.return_value = 0
        list_nodes.return_value = []
        expected_json = json.dumps({"token": "token"})
        fetch.return_value = ResponseBuffer(expected_json.encode())
        exp_info_res = {"items": []}

        with patch.object(self.api, 'get_experiment_info',
                          Mock(return_value=exp_info_res)):
            iotlabwscli.parser.main([])
            list_nodes.assert_called_with(self.api, 123, None, None)
            assert start.call_count == 0

    def test_main_fetch_failed(self, fetch, list_nodes, start):
        # pylint:disable=no-self-use
        """Run the parser.main."""
        fetch.side_effect = tornado.httpclient.HTTPClientError(123)
        iotlabwscli.parser.main([])
        assert list_nodes.call_count == 0
        assert start.call_count == 0
