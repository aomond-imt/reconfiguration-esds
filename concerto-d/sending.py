#!/usr/bin/env python
import json

import yaml
from esds.node import Node
import os

from esds.plugins.power_states import PowerStates, PowerStatesComms

current_dir_name = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(1, f"{current_dir_name}/..")
from simulation_functions import execution_work


def execute(api: Node):
    # Init
    with open(api.args["expe_config_file"]) as f:
        expe_config = yaml.safe_load(f)
        title = expe_config["title"]
        uptimes = expe_config["uptimes_nodes"]
        esds_data = expe_config

    tot_reconf_time, tot_reconf_flat_time, tot_no_reconf_time, tot_sleeping_time, node_conso, comms_cons = execution_work(
        api, uptimes[api.node_id], esds_data["reconf_periods_per_node"][api.node_id], esds_data["max_execution_duration"], "sending"
    )

    results = {
        "tot_reconf_time": round(tot_reconf_time, 2),
        "tot_reconf_flat_time": round(tot_reconf_flat_time, 2),
        "tot_no_reconf_time": round(tot_no_reconf_time, 2),
        "tot_sleeping_time": round(tot_sleeping_time, 2),
        "max_execution_time": round(tot_reconf_flat_time + tot_no_reconf_time + tot_sleeping_time, 2),
        "node_conso": f"{round(node_conso, 2)}J",
        "comms_cons": f"{round(comms_cons, 2)}J",
    }
    with open(f"/tmp/results/{title}/{api.node_id}.yaml", "w") as f:
        yaml.safe_dump(results, f)

    print(tot_reconf_time)
    print(tot_reconf_flat_time)
    print(tot_no_reconf_time)
    print(tot_sleeping_time)

    expected_t0_ud0_15_25 = {
        0: {
            "tot_reconf_time": 61.06,
            "tot_sending_time": 392.78,
            "tot_sleeping_time": 1394.66,
        },
        1: {
            "tot_reconf_time": 3.91,
            "tot_sending_time": 346.09,
            "tot_sleeping_time": 1497.5,
        }
    }
