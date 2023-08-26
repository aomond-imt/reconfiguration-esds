#!/usr/bin/env python
import yaml
from esds.node import Node
import os

from esds.plugins.power_states import PowerStatesComms


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
            api.log(f"Removing: node_id: {node_id} nb_nodes: {nb_nodes}")
            return
        else:
            api.log(f"Ok: {node_id} nb_nodes: {nb_nodes}")

        title = expe_config["title"]
        node_uptimes = expe_config["uptimes_periods_per_node"][node_id]
        max_execution_duration = expe_config["max_execution_duration"]

    # Version concerto_d parameters
    commsConso = api.args["commsConso"]
    version = "async" if "async" in title else "sync"
    if version == "sync":
        interface_name = f"eth0"
    else:
        interface_name = f"eth0Router"

    api.log(f"Interface: {interface_name}")
    tot_sending_time_flat, tot_no_sending_time_flat = 0, 0
    tot_msg_received, tot_msg_responded = {}, {}
    sending_cons = PowerStatesComms(api)
    sending_cons.set_power(interface_name, 0, commsConso, commsConso)

    api.turn_off()
    for up_start, up_end in node_uptimes:
        # Sleeping period (no receive)
        wait_before_start = up_start - api.read("clock")
        api.log(f"Waiting {wait_before_start} before starting")
        api.wait(wait_before_start)

        # Uptime period
        api.turn_on()
        while api.read("clock") < up_end:
            code, data = api.receivet(interface_name, timeout=up_end - api.read("clock"))
            api.log(f"Received: {data}")
            if data is not None:
                sender_id, receiver_id, data_to_send = data
                # Save msg received
                if data_to_send not in tot_msg_received.keys():
                    tot_msg_received[data_to_send] = 1
                else:
                    tot_msg_received[data_to_send] += 1
                if (version == "sync" and receiver_id == node_id) or (version == "async" and simulation_functions.is_router(node_id, nb_nodes)):
                    api.log(f"Sending response to {sender_id}")
                    # Send response
                    start_send = api.read("clock")
                    api.sendt(interface_name, node_id, data_to_send, sender_id, timeout=up_end - api.read("clock"))
                    tot_sending_time_flat += api.read("clock") - start_send
                    # Save msg responded
                    if data_to_send not in tot_msg_responded.keys():
                        tot_msg_responded[data_to_send] = 1
                    else:
                        tot_msg_responded[data_to_send] += 1
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
        "tot_msg_received": tot_msg_received,
        "tot_msg_responded": tot_msg_responded,
    }
    simulation_functions.print_esds_node_results(results, api)
    results_categ = "receives"
    with open(f"{os.environ['HOME']}/reconfiguration-esds/concerto-d-results/results/{results_categ}/{title}/{node_id}.yaml", "w") as f:
        yaml.safe_dump(results, f)

