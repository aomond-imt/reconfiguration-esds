#!/usr/bin/env python
import json

from esds.node import Node


# def execute(api: Node):
#     api.wait(250)
#     api.sendt("eth0","Hello World!",1,1, 50)
#     api.turn_off()


def execute(api: Node):
    # uptimes = json.load(open("node_scenarios.json"))
    api.turn_off()
    # api.log(f"Starting client node {api.node_id}")
    api.wait(500)
    # api.sendt("eth0","Hello World!",1,1, 50)
    api.turn_off()
