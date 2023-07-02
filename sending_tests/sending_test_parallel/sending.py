#!/usr/bin/env python
import json
from esds.node import Node

import os

from esds.plugins.power_states import PowerStatesComms

current_dir_name = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(1, f"{current_dir_name}/../..")

from simulation_functions import execution_work
import test_functions


def execute(api: Node):
    comms_cons = PowerStatesComms(api)
    comms_cons.set_power("eth0", 0, 0.1, 0.1)
    comms_cons.set_power("eth1", 0, 0.1, 0.1)

    if api.node_id == 0:
        api.turn_on()
        api.send("eth0", 1, 1, 1)
        api.send("eth1", 1, 1, 2)
        api.send("eth0", 1, 1, 3)
        api.send("eth0", 1, 1, 4)

    api.turn_off()
