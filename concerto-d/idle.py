#!/usr/bin/env python
import yaml
from esds.node import Node
import os

from esds.plugins.power_states import PowerStates

current_dir_name = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(1, f"{current_dir_name}/..")

import simulation_functions

def execute(api: Node):
    node_id = api.node_id % api.args["nodes_per_batch"]

    # Init
    with open(api.args["expe_config_file"]) as f:
        expe_config = yaml.safe_load(f)

        # Check if nb_deps is crossed
        nb_nodes = expe_config["nb_nodes"]
        if node_id >= nb_nodes:
            api.turn_off()
            print("dismmissing")
            return

        title = expe_config["title"]
        node_uptimes = expe_config["uptimes_periods_per_node"][node_id]
        max_execution_duration = expe_config["max_execution_duration"]

    print("got here")
    tot_uptime, tot_sleeping_time = 0, 0
    idle_cons = PowerStates(api, 0)
    idle_cons.set_power(0)
    if not simulation_functions.is_router(node_id, nb_nodes):
        idle_power = api.args["idleConso"]
    else:
        idle_power = api.args["idleConso"] + api.args["stressConso"]

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
    if abs(remaining_sleeping_duration) <= 0.0001:
        remaining_sleeping_duration = 0
    api.wait(remaining_sleeping_duration)
    tot_sleeping_time += remaining_sleeping_duration

    results = {
        "is_router": simulation_functions.is_router(node_id, nb_nodes),
        "tot_uptime": tot_uptime,
        "tot_sleeping_time": tot_sleeping_time,
        "node_conso": round(idle_cons.energy, 2),
        "comms_cons": 0,
    }
    simulation_functions.print_esds_node_results(results, api)
    execution_dir = f"{title}-{api.args['stressConso']}-{api.args['idleConso']}-{api.args['nameTechno']}-{api.args['typeSynchro']}"
    num_run = api.args["num_run"]
    with open(f"{os.environ['HOME']}/reconfiguration-esds/concerto-d-results/{num_run}/results/idles/{execution_dir}/{node_id}.yaml", "w") as f:
        yaml.safe_dump(results, f)
