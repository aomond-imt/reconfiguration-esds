#!/usr/bin/env python
import json

from esds.node import Node
from esds.plugins.power_states import PowerStates, PowerStatesComms


def execute(api: Node):
    sending_cons = PowerStatesComms(api)
    sending_cons.set_power("eth0", 0, 0.1, 0.1)
    api.turn_on()
    api.sendt("eth0", "zefoij", 30, 1, timeout=30)
    api.turn_off()

    sending_cons.report_energy()
