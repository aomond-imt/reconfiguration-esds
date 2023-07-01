#!/usr/bin/env python
import json

import yaml
from esds.node import Node
from esds.plugins.power_states import PowerStates, PowerStatesComms

OFF_POWER = 0
ON_POWER = 0.4
PROCESS_POWER = 1  # TODO model energetic
LORA_POWER = 0.16


def execute(api: Node):
    # Init
    with open("node_scenarios.json") as f:
        uptimes = json.load(f)
    with open("/tmp/esds_generated_data_ud0_od0_15_25_sync_deploy_T0.yaml") as f:
        esds_data = yaml.safe_load(f)

    duration = 50
    node_uptimes = uptimes[api.node_id]
    reconf_periods_per_node = esds_data["reconf_periods_per_node"][api.node_id]
    sending_periods_per_node = esds_data["sending_periods_per_node"][api.node_id]
    max_exec_duration = esds_data["max_execution_duration"]
    interface_name = "eth0"

    # Start expe
    ### Setup node power consumption
    node_cons = PowerStates(api, 0)
    comms_cons = PowerStatesComms(api)
    comms_cons.set_power(interface_name, 0, LORA_POWER, LORA_POWER)

    ### Run expe
    api.turn_off()
    node_cons.set_power(OFF_POWER)
    tot_reconf_time = 0
    tot_no_reconf_time = 0
    tot_sleeping_time = 0
    sleep_start = 0

    def c():
        return api.read("clock")

    for uptime, _ in node_uptimes:
        if uptime != -1:
            # Off period
            sleeping_time = min(uptime, max_exec_duration) - c()
            api.log(f"Sleeping for: {round(sleeping_time, 2)}s")
            api.wait(sleeping_time)
            tot_sleeping_time += c() - sleep_start

            # On period
            ## No reconf period
            api.turn_on()
            uptime_end = uptime + duration
            node_cons.set_power(ON_POWER)
            print(reconf_periods_per_node)
            for start, end, nb_processes in reconf_periods_per_node:
                if nb_processes > 0 and uptime <= start < uptime_end:
                    ## No reconf period
                    wait_before_reconf_start = max(start, c()) - c()
                    api.log(f"Waiting for action start: {round(wait_before_reconf_start, 2)}s")
                    tot_no_reconf_time += wait_before_reconf_start
                    api.wait(wait_before_reconf_start)

                    ## Reconf period
                    node_cons.set_power(ON_POWER + nb_processes * PROCESS_POWER)  # TODO model energetic
                    action_duration = end - start
                    api.log(f"Action duration: {round(action_duration, 2)}")
                    api.wait(action_duration)
                    tot_reconf_time += end - start

                    ## No reconf period
                    node_cons.set_power(ON_POWER)

            ## No reconf period, wait until sleeping
            remaining_waiting_duration = min(uptime_end, max_exec_duration) - c()
            if remaining_waiting_duration > 0:
                api.log(f"End of uptime period in: {round(remaining_waiting_duration, 2)}s")
                tot_no_reconf_time += remaining_waiting_duration
                api.wait(remaining_waiting_duration)

            # Off period
            api.turn_off()
            node_cons.set_power(OFF_POWER)
            sleep_start = c()
            if c() >= max_exec_duration:
                api.log(f"Threshold reached: {max_exec_duration}s. End of choreography")
                break

    expected = {
        0: {
            "tot_reconf_time": 61.06,
            "tot_sending_time": 392.44,
            "tot_sleeping_time": 1394,
        },
        1: {
            "tot_reconf_time": 3.91,
            "tot_sending_time": 346.09,
            "tot_sleeping_time": 1497.5,
        }
    }

    api.log(f"tot_reconf_time: {tot_reconf_time}")
    api.log(f"tot_sleeping_time: {tot_sleeping_time}")

    ### Gather results
    node_cons.report_energy()
    comms_cons.report_energy()
