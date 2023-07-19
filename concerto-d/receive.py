#!/usr/bin/env python
import yaml
from esds.node import Node
import os

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
        receive_periods_per_node = expe_config["receive_periods_per_node"]
        max_execution_duration = expe_config["max_execution_duration"]

    tot_receiving_time, tot_receiving_flat_time, tot_no_receiving_time, tot_sleeping_time, tot_working_time_dict, tot_working_time_flat_dict, node_conso, comms_cons = execution_work(
        api, uptimes[api.node_id % 6], receive_periods_per_node[api.node_id % 6], max_execution_duration, "receive"
    )

    results = {
        "tot_receiving_time": tot_working_time_dict,
        "tot_receiving_flat_time": tot_working_time_flat_dict,
        "tot_no_receiving_time": round(tot_no_receiving_time, 2),
        "tot_sleeping_time": round(tot_sleeping_time, 2),
        "node_conso": f"{round(node_conso, 2)}J",
        "comms_cons": f"{round(comms_cons, 2)}J",
    }
    for key, val in results.items():
        print(f"{key}: {val}")
    with open(f"/tmp/results/receives/{title}/{api.node_id % 6}.yaml", "w") as f:
        yaml.safe_dump(results, f)