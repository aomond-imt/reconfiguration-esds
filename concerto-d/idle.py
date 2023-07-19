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
        node_uptimes = expe_config["uptimes_periods_per_node"][api.node_id % 6]
        max_execution_duration = expe_config["max_execution_duration"]
    tot_uptime, tot_sleeping_time = 0, 0
    idle_cons = PowerStates(api, 0)
    idle_cons.set_power(0)

    api.turn_off()
    for start, end in node_uptimes:
        # Sleeping period
        sleeping_duration = start - api.read("clock")
        api.wait(sleeping_duration)
        tot_sleeping_time += sleeping_duration

        # Uptime period
        api.turn_on()
        idle_cons.set_power(0.4)
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
        "node_conso": f"{round(idle_cons.energy, 2)}J",
        "comms_cons": f"0J",
    }
    for key, val in results.items():
        print(f"{key}: {val}")
    with open(f"/tmp/results/idles/{title}/{api.node_id % 6}.yaml", "w") as f:
        yaml.safe_dump(results, f)