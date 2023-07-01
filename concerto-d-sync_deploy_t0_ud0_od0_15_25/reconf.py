#!/usr/bin/env python
import json

import yaml
from esds.node import Node
import os
current_dir_name = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(1, f"{current_dir_name}/..")
from simulation_functions import execution_reconf


def execute(api: Node):
    # Init
    with open(f"{current_dir_name}/node_scenarios.json") as f:
        uptimes = json.load(f)
    with open("/tmp/esds_generated_data_ud0_od0_15_25_sync_deploy_T0.yaml") as f:
        esds_data = yaml.safe_load(f)

    expected = {
        0: {
            "tot_reconf_time": 61.06,
            "tot_sending_time": 392.44,
            "tot_sleeping_time": 1394,
        },
        1: {
            "tot_reconf_time": 3.91,
            "tot_sending_time": 346.09,
            "tot_sleeping_time": 1497.5,
        }
    }

    execution_reconf(api, uptimes[api.node_id], esds_data["reconf_periods_per_node"][api.node_id], esds_data["max_execution_duration"])
