#!/usr/bin/env python
import json
from esds.node import Node

import os

from esds.plugins.power_states import PowerStatesComms, PowerStates

current_dir_name = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(1, f"{current_dir_name}/../..")

from simulation_functions import execution_work
import test_functions


def execute(api: Node):
    for i in range(3):
        api.sendt("eth0", 1, 1, i, timeout=1)
    # api.sendt("eth0", 1, 1, 1, timeout=1)
    # api.sendt("eth0", 1, 1, 1, timeout=1)
