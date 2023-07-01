#!/usr/bin/env python
import json
from esds.node import Node

import os
current_dir_name = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(1, f"{current_dir_name}/../..")

from simulation_functions import execution_reconf
import test_functions


def execute(api: Node):
    # Init
    node_uptimes = [
        [0, 1], [155, 1]
    ]
    reconf_periods_per_node = [[5.23, 54.2, 1]]
    max_execution_duration = 160.5

    expected_tot_reconf_time = 48.97     # 54.2 - 5.23
    expected_tot_no_reconf_time = 10.73  # 5.23 + 5.5
    expected_tot_sleeping_time = 100.8   # 155 - 50 - 5.2
    tot_reconf_time, tot_no_reconf_time, tot_sleeping_time, node_conso, comms_cons = execution_reconf(api, node_uptimes, reconf_periods_per_node, max_execution_duration)

    test_functions.print_assertions("Reconf time", expected_tot_reconf_time, tot_reconf_time)
    test_functions.print_assertions("No reconf time", expected_tot_no_reconf_time, tot_no_reconf_time)
    test_functions.print_assertions("Sleeping time", expected_tot_sleeping_time, tot_sleeping_time)
