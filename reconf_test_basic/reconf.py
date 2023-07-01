#!/usr/bin/env python
import json
from esds.node import Node

import os
current_dir_name = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(1, f"{current_dir_name}/..")

from simulation_functions import execution_reconf


def execute(api: Node):
    # Init
    node_uptimes = [
        [0, 1]
    ]
    reconf_periods_per_node = [[5, 10, 1]]
    max_execution_duration = 20

    expected_tot_reconf_time = 5
    expected_tot_no_reconf_time = 15
    expected_tot_sleeping_time = 0
    tot_reconf_time, tot_no_reconf_time, tot_sleeping_time = execution_reconf(api, node_uptimes, reconf_periods_per_node, max_execution_duration)

    print(expected_tot_reconf_time, tot_reconf_time)
    print(expected_tot_no_reconf_time, tot_no_reconf_time)
    print(expected_tot_sleeping_time, tot_sleeping_time)
