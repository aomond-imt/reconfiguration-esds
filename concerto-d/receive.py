#!/usr/bin/env python
import yaml
from esds.node import Node
import os

from esds.plugins.power_states import PowerStatesComms


current_dir_name = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(1, f"{current_dir_name}/..")

import simulation_functions

LORA_POWER = 0.16
LONGER_POWER = 0.16
FREQUENCE_POLLING = 1
NB_POLL_PER_SEC = 10


def execute(api: Node):
    node_id = api.node_id % api.args["nodes_per_batch"]

    # Init
    with open(api.args["expe_config_file"]) as f:
        expe_config = yaml.safe_load(f)

        # Check if nb_deps is crossed
        nb_deps = expe_config["nb_deps"]
        if node_id not in [0, 6] and node_id > nb_deps:
            return

        title = expe_config["title"]
        node_uptimes = expe_config["uptimes_periods_per_node"][node_id]
        max_execution_duration = expe_config["max_execution_duration"]

    # Version concerto_d parameters
    if "async" not in title:
        interface_name = f"eth0"
    else:
        interface_name = f"eth0Router"
    commsConso = api.args["commsConso"]
    api.log(f"Interface: {interface_name}")
    tot_sending_time_flat, tot_no_sending_time_flat = 0, 0
    sending_cons = PowerStatesComms(api)
    sending_cons.set_power(interface_name, 0, commsConso, commsConso)

    size = 257
    api.turn_off()
    for up_start, up_end in node_uptimes:
        # Sleeping period (no receive)
        wait_before_start = up_start - api.read("clock")
        api.log(f"Waiting {wait_before_start} before starting")
        api.wait(wait_before_start)

        # Uptime period
        api.turn_on()
        while api.read("clock") < up_end:
            timeout = up_end - api.read("clock")
            code, data = api.receivet(interface_name, timeout=timeout)
            api.log(f"Received: {data}")
            if data is not None:
                sender_id, receiver_id = data
                print(sender_id, receiver_id, node_id)
                if receiver_id == node_id:
                    api.log(f"Sending response to {receiver_id}")
                    # Send response
                    start_send = api.read("clock")
                    api.sendt(interface_name, node_id, size, sender_id, timeout=timeout)
                    tot_sending_time_flat += api.read("clock") - start_send

            else:
                api.log("Received None data")

        # Sleeping period
        api.turn_off()
    remaining_no_sending_duration = max_execution_duration - api.read("clock")
    api.log(f"Waiting {remaining_no_sending_duration} before terminating")
    api.wait(remaining_no_sending_duration)
    sending_cons_energy = sending_cons.get_energy()

    results = {
        f"tot_receive_flat_time": tot_sending_time_flat,
        f"tot_no_receive_time": round(tot_no_sending_time_flat, 2),
        "node_conso": 0,
        "comms_cons": float(round(sending_cons_energy, 2)),
    }
    simulation_functions.print_esds_node_results(results, api)
    results_categ = "receives"
    with open(f"/home/aomond/reconfiguration-esds/concerto-d-results/results/{results_categ}/{title}/{node_id}.yaml",
              "w") as f:
        yaml.safe_dump(results, f)

