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
    uptimes = {
        0: [[0, 1], [300, 0]],
        1: [[10, 1], [300, 1]],
        2: [[0, 1], [200.5, 0]],
    }
    reconf_periods_per_node = {
        0: [[0, 50, 2]],
        1: [[15, 55, 1]],
        2: [[5, 10, 0], [10, 20, 1], [200.5, 200.6, 5]],
    }

    max_execution_duration = 210

    expected_results_per_node = {
        0: {
            "expected_tot_reconf_time": 100,     # (50 - 0) * 2
            "expected_tot_no_reconf_time": 0,
            "expected_tot_sleeping_time": 160,   # 210 - 50
        },
        1: {
            "expected_tot_reconf_time": 40,     # (55 - 15) * 1
            "expected_tot_no_reconf_time": 10,
            "expected_tot_sleeping_time": 160,  # 10 + 210 - 60
        },
        2: {
            "expected_tot_reconf_time": 10.5,     # (10 - 5) * 0 + (20 - 10) * 1 + (200.6 - 200.5) * 5
            "expected_tot_no_reconf_time": 49.4,  # 10 + 30 + 210-200.6
            "expected_tot_sleeping_time": 150.5,  # 200.5 - 50
        }
    }
    tot_reconf_time, tot_no_reconf_time, tot_sleeping_time, node_conso, comms_cons = execution_reconf(api, uptimes[api.node_id], reconf_periods_per_node[api.node_id], max_execution_duration)

    expected_resuts_node = expected_results_per_node[api.node_id]
    test_functions.print_assertions("Reconf time", expected_resuts_node["expected_tot_reconf_time"], tot_reconf_time)
    test_functions.print_assertions("No reconf time", expected_resuts_node["expected_tot_no_reconf_time"], tot_no_reconf_time)
    test_functions.print_assertions("Sleeping time", expected_resuts_node["expected_tot_sleeping_time"], tot_sleeping_time)
