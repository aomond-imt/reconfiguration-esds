#!/usr/bin/env python
import yaml
from esds.node import Node
import os

from esds.plugins.power_states import PowerStatesComms

current_dir_name = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(1, f"{current_dir_name}/..")

LORA_POWER = 0.16


def execute(api: Node):
    # Init
    with open(api.args["expe_config_file"]) as f:
        expe_config = yaml.safe_load(f)
        title = expe_config["title"]
        node_uptimes = expe_config["uptimes_periods_per_node"][api.node_id % 7]
        receive_periods_per_node = expe_config["receive_periods_per_node"][api.node_id % 7]
        max_execution_duration = expe_config["max_execution_duration"]
    tot_receive_time_flat, tot_no_receive_time_flat = 0, 0
    interface_name = "ethRouterReceive" if "async" in title else "ethReceive"
    # interface_name = "ethReceive"
    receive_cons = PowerStatesComms(api)
    receive_cons.set_power(interface_name, 0, LORA_POWER, LORA_POWER)

    size = 1
    api.turn_off()
    for up_start, up_end in node_uptimes:
        # Sleeping period (no receive)
        wait_before_start = up_start - api.read("clock")
        api.log(f"Waiting {wait_before_start} before starting")
        api.wait(wait_before_start)

        # Uptime period
        api.turn_on()
        for start, end, node_send in receive_periods_per_node:
            # Search receive periods of the current uptime
            if node_send != {} and up_start <= start and end <= up_end:
                # No receive period
                no_receive_period = start - api.read("clock")
                api.log(f"Wait {no_receive_period} until next period")
                api.wait(no_receive_period)
                tot_no_receive_time_flat += no_receive_period

                # Receive period
                api.log("Start receiving")
                while api.read("clock") < end:
                    for node_id, count in node_send.items():
                        if api.read("clock") < end:
                            end_period = end - api.read("clock")
                            data_to_send = min(size * count, end_period)
                            api.sendt(interface_name, 1, data_to_send, 1, timeout=data_to_send)
                            tot_receive_time_flat += data_to_send
        remaining_uptime = up_end - api.read("clock")
        api.log(f"Waiting remaining uptime {remaining_uptime}")
        api.wait(remaining_uptime)
        tot_no_receive_time_flat += remaining_uptime

        # Sleeping period
        api.turn_off()
    remaining_no_receive_duration = max_execution_duration - api.read("clock")
    api.log(f"Waiting {remaining_no_receive_duration} before terminating")
    api.wait(remaining_no_receive_duration)
    receive_cons_energy = receive_cons.get_energy()

    results = {
        "tot_receive_flat_time": tot_receive_time_flat,
        "tot_no_receive_time": round(tot_no_receive_time_flat, 2),
        "node_conso": 0,
        "comms_cons": float(round(receive_cons_energy, 2)),
    }
    for key, val in results.items():
        print(f"{key}: {val}")
    with open(f"/tmp/results/receives/{title}/{api.node_id % 7}.yaml", "w") as f:
        yaml.safe_dump(results, f)
