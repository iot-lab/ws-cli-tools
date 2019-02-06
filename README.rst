Websocket CLI Tools
===================

|PyPI| |Travis| |Codecov|

**Websocket CLI Tools** provides a set of commands for interacting remotely and
easily with IoT-Lab nodes using the Websosket protocol.

**Websocket CLI Tools** can be used in conjunction with the
`IoT-Lab CLI Tools <https://github.com/iot-lab/cli-tools>`_ commands like
`iotlab-auth` and `iotlab-experiment`.

Installation:
-------------

You need python `pip <https://pip.pypa.io/en/stable/>`_.
To install ws-cli-tools, use pip (or pip3 for Python 3)::

    $ pip install iotlabwscli --user

Example:
--------

Start an experiment, wait for it to be ready and connect to the serial port:

.. code-block::

    $ iotlab-experiment submit -d 120 -l saclay,m3,1,tutorial_m3.elf
    {
        "id": 65535
    }
    $ iotlab-experiment wait
    Waiting that experiment 65535 gets in state Running
    "Running"
    $ iotlab-ws
    Using custom api_url: https://www.iot-lab.info/rest/
    Connected to m3-1.saclay

    h
    m3-1.saclay:
    m3-1.saclay:
    m3-1.saclay: IoT-LAB Simple Demo program
    m3-1.saclay: Type command
    m3-1.saclay: 	h:	print this help
    m3-1.saclay: 	t:	temperature measure
    m3-1.saclay: 	l:	luminosity measure
    m3-1.saclay: 	p:	pressure measure
    m3-1.saclay: 	u:	print node uid
    m3-1.saclay: 	d:	read current date using control_node
    m3-1.saclay: 	s:	send a radio packet
    m3-1.saclay: 	b:	send a big radio packet
    m3-1.saclay: 	e:	toggle leds blinking
    m3-1.saclay:
    e
    m3-1.saclay: cmd >
    m3-1.saclay: leds > off
    m3-1.saclay:
    l
    m3-1.saclay: cmd > Luminosity measure: 2.4414062 lux
    m3-1.saclay:
    ^CExiting
    0

.. |PyPI| image:: https://badge.fury.io/py/iotlabwscli.svg
   :target: https://badge.fury.io/py/iotlabwscli
   :alt: PyPI package status

.. |Travis| image:: https://travis-ci.org/iot-lab/ws-cli-tools.svg?branch=master
   :target: https://travis-ci.org/iot-lab/ws-cli-tools
   :alt: Travis build status

.. |Codecov| image:: https://codecov.io/gh/iot-lab/ws-cli-tools/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/iot-lab/ws-cli-tools/branch/master
   :alt: Codecov coverage status
