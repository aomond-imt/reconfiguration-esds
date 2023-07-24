#!/usr/bin/env python
import json

from esds.node import Node
from esds.plugins.power_states import PowerStatesComms


# def execute(api: Node):
#     api.wait(250)
#     api.sendt("eth0","Hello World!",1,1, 50)
#     api.turn_off()


def execute(api: Node):
    sending_cons = PowerStatesComms(api)
    sending_cons.set_power("eth0", 0, 0.1, 0.1)
    api.turn_on()
    # api.log(f"Starting client node {api.node_id}")
    api.sendt("eth0", "zefoij", 60, 1, timeout=60)
    api.wait(500)
    # api.sendt("eth0","Hello World!",1,1, 50)
    api.turn_off()
    sending_cons.report_energy()
