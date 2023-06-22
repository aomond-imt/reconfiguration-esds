#!/usr/bin/env python
import json

from esds.node import Node
from esds.plugins.power_states import PowerStates, PowerStatesComms


# def execute(api: Node):
#     api.wait(250)
#     api.sendt("eth0","Hello World!",1,1, 50)
#     api.turn_off()

OFF_POWER = 0
ON_POWER = 0.4


def execute(api: Node):
    # Init
    uptimes = json.load(open("node_scenarios.json"))
    duration = 50
    dep_uptimes = uptimes[api.node_id]
    interface_name = "eth0"

    # Start expe
    ### Setup node power consumption
    node_cons = PowerStates(api, 0)
    comms_cons = PowerStatesComms(api)
    comms_cons.set_power(interface_name, 0, 0.16, 0.16)

    ### Run expe
    api.log(f"Starting dep node")
    api.turn_off()
    node_cons.set_power(OFF_POWER)
    for uptime, _ in dep_uptimes:
        if uptime != -1:
            api.wait(uptime - api.read("clock"))  # Wait being off
            api.turn_on()
            node_cons.set_power(ON_POWER)
            while api.read("clock") < uptime + duration:
                api.receivet(interface_name, duration)
            api.turn_off()
            node_cons.set_power(OFF_POWER)

    ### Gather results
    node_cons.report_energy()
    comms_cons.report_energy()
