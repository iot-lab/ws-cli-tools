
Websocket CLI Tools
===================

**Websocket CLI Tools** provides a set of commands for interacting remotely and
easily with IoT-Lab nodes using the Websosket protocol.

**Websocket CLI Tools** can be used in conjunction with the
`IoT-Lab CLI Tools <https://github.com/iot-lab/cli-tools>`_ commands like
`iotlab-auth` and `iotlab-experiment`.

Installation:
-------------

You need python `pip <https://pip.pypa.io/en/stable/>`_.
To do a system-wide install of the ssh-cli-tools use pip (or pip3 for
Python 3)::

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
    Websocket connection opened

    cmd > h

    IoT-LAB Simple Demo program
    Type command
        h:	print this help
        t:	temperature measure
        l:	luminosity measure
        p:	pressure measure
        u:	print node uid
        d:	read current date using control_node
        s:	send a radio packet
        b:	send a big radio packet
        e:	toggle leds blinking

    cmd > ^CExiting
    0
