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
import pytest
from mock import Mock, patch

from iotlabwscli.parser import main

from .iotlabwscli_mock import MainMock, ResponseBuffer

# pylint: disable=too-many-public-methods
# pylint: disable=too-few-public-methods


class TestParser(MainMock):
    """Test websocket cli main parser."""

    _nodes = ['m3-1.saclay.iot-lab.info']

    @patch('iotlabwscli.client.start')
    @patch('iotlabcli.parser.common.list_nodes')
    @patch('tornado.httpclient.HTTPClient.fetch')
    def test_main_start(self, fetch, list_nodes, start):
        """Run the parser.main."""

        start.return_value = 0
        list_nodes.return_value = self._nodes
        expected_json = json.dumps({"token": "token"})
        fetch.return_value = ResponseBuffer(expected_json.encode())

        args = ['-l', 'saclay,m3,1']
        main(args)
        list_nodes.assert_called_with(self.api, 123, [self._nodes], None)
        start.assert_called_with(self.api.url, self._nodes[0], 123, "token")

        exp_info_res = {"items": [{"network_address": node}
                                  for node in self._nodes]}
        with patch.object(self.api, 'get_experiment_info',
                          Mock(return_value=exp_info_res)):
            list_nodes.return_value = []
            with pytest.raises(SystemExit):
                main(args)

        # exp_info_res = {"items": [{"network_address": node}
        #                           for node in self._nodes]}
        # with patch.object(self.api, 'get_experiment_info',
        #                   Mock(return_value=exp_info_res)):
        #     list_nodes.return_value = []
        #     args = ['flash-m3', 'firmware.elf']
        #     open_a8_parser.main(args)
        #     list_nodes.assert_called_with(self.api, 123, None, None)
        #     flash_m3.assert_called_with({'user': 'username', 'exp_id': 123},
        #                                 self._root_nodes,
        #                                 'firmware.elf', verbose=False)
