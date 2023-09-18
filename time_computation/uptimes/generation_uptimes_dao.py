import json
import os

import numpy as np

RANDOM_GENERATION_SEED = 1000
RANDOM_GENERATION_SEED_ADDITIONNAL = 2123

random_generator = np.random.default_rng(RANDOM_GENERATION_SEED_ADDITIONNAL)


def _generate_uptime_list(uptime_duration: float, nb_hours: int):
    min_uptime, max_uptime = 0, 3600
    uptimes_list = []
    offset = max_uptime + 300 + 5
    for hour in range(nb_hours):
        uptime = round(random_generator.uniform(min_uptime, max_uptime) + offset*hour, 3)
        uptimes_list.append((uptime, uptime_duration))

    return uptimes_list


def _generate_uptimes_list_for_nodes(nb_nodes: int, uptime_duration):
    nodes_uptimes_list = []
    nb_hours = 24 * 30
    for node_num in range(nb_nodes):
        uptimes_list = _generate_uptime_list(uptime_duration, nb_hours)
        nodes_uptimes_list.append(uptimes_list)

    return nodes_uptimes_list


for i in range(100, 200):
    print(str(i) + "...")
    uptime_durations_list = [60, 120, 180]
    for uptime_duration in uptime_durations_list:
        nodes_uptimes_list = _generate_uptimes_list_for_nodes(31, uptime_duration)
        os.makedirs(str(i), exist_ok=True)
        with open(f"{i}/uptimes-dao-{uptime_duration}-sec.json", "w") as f:
            json.dump(nodes_uptimes_list, f)
# print(_generate_uptimes_list_for_nodes(6)[0])
