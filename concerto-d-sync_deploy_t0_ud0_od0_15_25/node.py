#!/usr/bin/env python
import json

import yaml
from esds.node import Node
from esds.plugins.power_states import PowerStates, PowerStatesComms

OFF_POWER = 0
ON_POWER = 0.4 + 0.16        # TODO: assume sending all the time, remove this assumption and be more fine grained
LORA_POWER = 0.16
RECONF_POWER = ON_POWER + 1  # TODO: refine by including number of // tasks


def execute(api: Node):
    # Init
    with open("node_scenarios.json") as f:
        uptimes = json.load(f)
    with open("/tmp/esds_generated_data_ud0_od0_15_25.yaml") as f:
        reconf_periods = yaml.safe_load(f)

    duration = 50
    dep_uptimes = uptimes[api.node_id]
    dep_reconf_periods = sorted(reconf_periods["reconf_periods"][api.node_id], key=lambda item: item[0])
    interface_name = "eth0"
    max_exec_duration = reconf_periods["max_execution_duration"]

    # Start expe
    ### Setup node power consumption
    node_cons = PowerStates(api, 0)
    comms_cons = PowerStatesComms(api)
    comms_cons.set_power(interface_name, 0, LORA_POWER, LORA_POWER)

    ### Run expe
    api.log(f"Starting dep node")
    api.turn_off()
    node_cons.set_power(OFF_POWER)
    tot_reconf_time = 0
    tot_sleeping_time = 0
    tot_sending_time = 0
    sleep_start = 0

    def c():
        return api.read("clock")

    for uptime, _ in dep_uptimes:
        if uptime != -1:
            # Off period
            api.wait(min(uptime, max_exec_duration) - c())
            tot_sleeping_time += c() - sleep_start

            # On period
            api.turn_on()
            uptime_end = uptime + duration
            node_cons.set_power(ON_POWER)
            send_start = c()
            for start, end in dep_reconf_periods:
                if uptime <= start < uptime_end:
                    api.wait(start - c())
                    tot_sending_time += c() - send_start
                    node_cons.set_power(RECONF_POWER)
                    api.wait(end - start)
                    tot_reconf_time += end-start
                    node_cons.set_power(ON_POWER)
                    send_start = c()

            remaining_waiting_duration = min(uptime_end, max_exec_duration) - c()
            if remaining_waiting_duration > 0:
                api.wait(remaining_waiting_duration)
            # while c() < uptime + duration:
            #     # api.receivet(interface_name, duration)
            #     api.sendt(interface_name, 1, 10, 1, uptime + duration - c())
            tot_sending_time += c() - send_start

            # Off period
            api.turn_off()
            node_cons.set_power(OFF_POWER)
            sleep_start = c()
            if c() >= max_exec_duration:
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
    api.log(f"tot_sending_time: {tot_sending_time}")
    api.log(f"tot_sleeping_time: {tot_sleeping_time}")

    ### Gather results
    node_cons.report_energy()
    comms_cons.report_energy()
