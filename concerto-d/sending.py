#!/usr/bin/env python
import json

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
    if api.node_id % 7 not in [0, 6] and api.node_id > api.args["nbDeps"]:
        return

    simulation_functions.sending(api, "sending")
