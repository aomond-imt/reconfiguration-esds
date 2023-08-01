#!/usr/bin/env python
import yaml
from esds.node import Node
import os

from esds.plugins.power_states import PowerStatesComms

import simulation_functions

current_dir_name = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(1, f"{current_dir_name}/..")

LORA_POWER = 0.16
LONGER_POWER = 0.16
FREQUENCE_POLLING = 1
NB_POLL_PER_SEC = 10


def execute(api: Node):
    simulation_functions.sending(api, "receive")
