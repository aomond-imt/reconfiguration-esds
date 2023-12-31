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


def execute(api: Node):
    node_id = api.node_id % api.args["nodes_per_batch"]

    # Init
    with open(api.args["expe_config_file"]) as f:
        expe_config = yaml.safe_load(f)

        # Check if nb_deps is crossed
        nb_nodes = expe_config["nb_nodes"]
        if node_id >= nb_nodes:
            api.turn_off()
            return

        title = expe_config["title"]
        node_uptimes = expe_config["uptimes_periods_per_node"][node_id]
        sending_periods_per_node = expe_config[f"sending_periods_per_node"][node_id]
        max_execution_duration = expe_config["max_execution_duration"]

    # Version concerto_d parameters
    if "async" not in title:
        interface_name = f"eth0"
    else:
        interface_name = f"eth0Router"
    commsConso = api.args["commsConso"]
    api.log(f"Interface: {interface_name}")
    tot_sending_time_flat, tot_no_sending_time_flat = 0, 0
    tot_msg_sent, tot_ack_received, tot_wait_polling = {}, {}, {}
    sending_cons = PowerStatesComms(api)
    sending_cons.set_power(interface_name, 0, commsConso, commsConso)

    size = 257
    name_techno = api.args["nameTechno"]
    bandwidth = 6250 if name_techno == "lora" else 25000  # lora or nbiot
    api.turn_off()
    for up_start, up_end in node_uptimes:
        # Sleeping period (no receive)
        wait_before_start = up_start - api.read("clock")
        if abs(wait_before_start) <= 0.0001:
            wait_before_start = 0
        api.log(f"Waiting {wait_before_start} before starting")
        api.wait(wait_before_start)

        # Uptime period
        api.turn_on()
        for start, end, node_send in sending_periods_per_node:
            # Search sending periods of the current uptime
            if node_send != {} and up_start <= start and end <= up_end:
                # No sending period
                no_sending_period = start - api.read("clock")
                if abs(no_sending_period) <= 0.0001:
                    no_sending_period = 0
                api.log(f"Wait {no_sending_period} until next period")
                api.wait(no_sending_period)
                tot_no_sending_time_flat += no_sending_period

                # Sending period
                api.log("Start sending")
                sending_start = api.read("clock")
                while api.read("clock") < end:
                    for sender_id, count in node_send.items():
                        if api.read("clock") < end:
                            data_to_send = size * count
                            api.sendt(interface_name, (node_id, sender_id, data_to_send), data_to_send, sender_id, timeout=end - api.read("clock"))
                            # Save nb msg sent
                            if data_to_send not in tot_msg_sent.keys():
                                tot_msg_sent[data_to_send] = 1
                            else:
                                tot_msg_sent[data_to_send] += 1

                            waiting_ack = min(end - api.read("clock"), size/bandwidth)
                            if abs(waiting_ack) <= 0.0001:
                                waiting_ack = 0
                            api.wait(waiting_ack)
                            # code, data = api.receivet(interface_name, timeout=min(end - api.read("clock"), (size/bandwidth)+0.0001))  # Put a little overhead for float operations precision
                            # api.log(f"Receive ack: {data}")
                            if data_to_send not in tot_ack_received.keys():
                                tot_ack_received[data_to_send] = 1
                            else:
                                tot_ack_received[data_to_send] += 1

                    if api.read("clock") < end:
                        wait_polling = min(FREQUENCE_POLLING, end - api.read("clock"))
                        if abs(wait_polling) <= 0.0001:
                            wait_polling = 0
                        api.wait(wait_polling)
                        # Save wait_polling
                        if wait_polling not in tot_wait_polling.keys():
                            tot_wait_polling[wait_polling] = 1
                        else:
                            tot_wait_polling[wait_polling] += 1
                tot_sending_time_flat += api.read("clock") - sending_start

        remaining_uptime = up_end - api.read("clock")
        if abs(remaining_uptime) <= 0.0001:
            remaining_uptime = 0
        api.log(f"Waiting remaining uptime {remaining_uptime}")
        api.wait(remaining_uptime)
        tot_no_sending_time_flat += remaining_uptime

        # Sleeping period
        api.turn_off()
    remaining_no_sending_duration = max_execution_duration - api.read("clock")
    if abs(remaining_no_sending_duration) <= 0.0001:
        remaining_no_sending_duration = 0
    api.log(f"Waiting {remaining_no_sending_duration} before terminating")
    api.wait(remaining_no_sending_duration)
    sending_cons_energy = sending_cons.get_energy()

    results = {
        f"tot_sending_flat_time": tot_sending_time_flat,
        f"tot_no_sending_time": round(tot_no_sending_time_flat, 2),
        "node_conso": 0,
        "comms_cons": float(round(sending_cons_energy, 2)),
        "tot_msg_sent": tot_msg_sent,
        "tot_ack_received": tot_ack_received,
        "tot_wait_polling": tot_wait_polling
    }
    simulation_functions.print_esds_node_results(results, api)
    params_joined = simulation_functions.get_params_joined({
        "stressConso": api.args['stressConso'],
        "idleConso": api.args['idleConso'],
        "nameTechno": api.args['nameTechno'],
        "typeSynchro": api.args['typeSynchro'],
    })
    execution_dir = f"{title}-{params_joined}"
    num_run = api.args["num_run"]
    with open(f"{os.environ['HOME']}/esds-executions-runs/{num_run}/esds-node-results/sends/{execution_dir}/{node_id}.yaml",
              "w") as f:
        yaml.safe_dump(results, f)
