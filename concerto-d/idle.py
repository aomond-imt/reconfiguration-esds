#!/usr/bin/env python
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
        node_uptimes = expe_config["uptimes_periods_per_node"][api.node_id % 7]
        max_execution_duration = expe_config["max_execution_duration"]

    if api.node_id % 7 not in [0, 6] and api.node_id > nb_deps:
        return

    tot_uptime, tot_sleeping_time = 0, 0
    idle_cons = PowerStates(api, 0)
    idle_cons.set_power(0)
    idle_power = api.args["idleConso"]

    api.turn_off()
    for start, end in node_uptimes:
        # Sleeping period
        sleeping_duration = start - api.read("clock")
        api.wait(sleeping_duration)
        tot_sleeping_time += sleeping_duration

        # Uptime period
        api.turn_on()
        idle_cons.set_power(idle_power)
        api.wait(end - start)
        tot_uptime += end - start

        # Sleeping period
        api.turn_off()
        idle_cons.set_power(0)

    remaining_sleeping_duration = max_execution_duration - api.read("clock")
    api.wait(remaining_sleeping_duration)
    tot_sleeping_time += remaining_sleeping_duration

    results = {
        "tot_uptime": tot_uptime,
        "tot_sleeping_time": tot_sleeping_time,
        "node_conso": round(idle_cons.energy, 2),
        "comms_cons": 0,
    }
    for key, val in results.items():
        print(f"{key}: {val}")
    with open(f"/home/aomond/reconfiguration-esds/concerto-d-results/results/idles/{title}/{api.node_id % 7}.yaml", "w") as f:
        yaml.safe_dump(results, f)
