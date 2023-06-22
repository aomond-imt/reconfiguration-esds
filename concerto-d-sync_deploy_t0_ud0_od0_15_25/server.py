#!/usr/bin/env python
import json

from esds.node import Node
from esds.plugins.power_states import PowerStates, PowerStatesComms


# def execute(api: Node):
#     uptimes = json.load(open("node_scenarios.json"))
#     uptimes_node = uptimes[0]
#     uptimes_target_node = uptimes[1]
#
#     for un_uptime, un_duration in uptimes_node:
#         for utn_uptime, utn_duration in uptimes_target_node:
#             overlap = min(un_uptime+un_duration, utn_uptime+utn_duration) - max(un_uptime, utn_uptime)
#             if overlap > 0:
#                 api.send("eth0", "Sending msg", 1, 1)
#
#     # api.turn_off()
#     # code, data=api.receive("eth0")
#     # api.log(f"{code}, {data}")
#     api.log(str(api.node_id))
#
#     api.turn_off()
    # api.wait(260)
    # api.turn_on()
    # code, data = api.receivet("eth0", 50)
    # api.log(f"{code} {data}")
    # api.turn_off()

# def execute(api: Node):
    # uptimes = json.load(open("node_scenarios.json"))
    # api.turn_on()
    # api.log(f"Starting node {api.node_id}")
    # api.log("Starting0 receive")
    # code0, data0 = api.receivet("eth0", 50)
    # api.log(f"{code0} {data0}")
    # api.log("Starting1 receive")
    # code1, data1 = api.receivet("eth1", 50)
    # api.log(f"{code1} {data1}")
    # api.turn_off()

OFF_POWER = 0
ON_POWER = 0.4


def execute(api: Node):
    # Init
    uptimes = json.load(open("node_scenarios.json"))
    duration = 50
    server_uptimes = uptimes[api.node_id]
    interface_name = "eth0"

    # Start expe
    ### Setup node power consumption
    node_cons = PowerStates(api, 0)
    comms_cons = PowerStatesComms(api)
    comms_cons.set_power(interface_name, 0, 0.16, 0.16)

    ### Run expe
    api.log(f"Starting server node")
    api.turn_off()
    node_cons.set_power(OFF_POWER)
    for uptime, _ in server_uptimes:
        api.wait(uptime - api.read("clock"))  # Wait being off
        api.turn_on()
        node_cons.set_power(ON_POWER)
        while api.read("clock") < uptime + duration:
            api.sendt(interface_name, 1, 25, 1, duration)
        # api.wait(duration)                    # Wait being on
        api.turn_off()
        node_cons.set_power(OFF_POWER)

    ### Gather results
    node_cons.report_energy()
    comms_cons.report_energy()
