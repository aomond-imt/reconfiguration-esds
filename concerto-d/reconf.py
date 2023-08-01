#!/usr/bin/env python
import json

import yaml
from esds.node import Node
import os

from esds.plugins.power_states import PowerStates

current_dir_name = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(1, f"{current_dir_name}/..")


def execute(api: Node):
    # Init
    with open(api.args["expe_config_file"]) as f:
        expe_config = yaml.safe_load(f)
        title = expe_config["title"]
        nb_deps = expe_config["nb_deps"]
        reconf_periods_per_node = expe_config["reconf_periods_per_node"][api.node_id % 7]
        max_execution_duration = expe_config["max_execution_duration"]

    if api.node_id % 7 not in [0, 6] and api.node_id > nb_deps:
        return

    tot_reconf_time, tot_flat_reconf_time, tot_no_reconf_time = 0, 0, 0
    reconf_cons = PowerStates(api, 0)
    reconf_cons.set_power(0)
    stress_power = api.args["stressConso"]

    api.turn_on()
    for start, end, nb_processes in reconf_periods_per_node:
        if nb_processes > 0:
            # No reconf period
            no_reconf_duration = start - api.read("clock")
            api.wait(no_reconf_duration)
            tot_no_reconf_time += no_reconf_duration

            # Reconf period
            reconf_duration = end - start
            reconf_duration_ponderee = reconf_duration * nb_processes
            reconf_cons.set_power(stress_power * nb_processes)
            api.wait(reconf_duration)
            tot_reconf_time += reconf_duration_ponderee
            tot_flat_reconf_time += reconf_duration

            # No reconf period
            reconf_cons.set_power(0)

    remaining_no_reconf_duration = max_execution_duration - api.read("clock")
    api.wait(remaining_no_reconf_duration)
    tot_no_reconf_time += remaining_no_reconf_duration

    results = {
        "tot_reconf_time": round(tot_reconf_time, 2),
        "tot_reconf_flat_time": round(tot_flat_reconf_time, 2),
        "tot_no_reconf_time": round(tot_no_reconf_time, 2),
        "node_conso": round(reconf_cons.energy, 2),
        "comms_cons": 0,
    }
    for key, val in results.items():
        print(f"{key}: {val}")
    with open(f"/home/aomond/reconfiguration-esds/concerto-d-results/results/reconfs/{title}/{api.node_id}.yaml", "w") as f:
        yaml.safe_dump(results, f)
