import yaml
from esds.plugins.power_states import PowerStatesComms

FREQUENCE_POLLING = 1
NB_POLL_PER_SEC = 10


def get_simulation_swepped_parameters():
    from execo_engine import sweep

    # parameters = {
    #     "stressConso": [0, 1.358],  # 1.339-1.339, 2.576-1.339, 2.697-1.339
    #     "idleConso": [1.339],
    #     "techno": [{"name": "lora", "bandwidth": "50kbps", "commsConso": 0.16},
    #                {"name": "nbiot", "bandwidth": "200kbps", "commsConso": 0.65}],
    #     "typeSynchro": ["pullc"]
    # }
    parameters = {
        "stressConso": [0, 1.358],  # 1.339-1.339, 2.576-1.339, 2.697-1.339
        "idleConso": [1.339],
        "techno": [{"name": "lora", "bandwidth": "50kbps", "commsConso": 0.16}],
        "typeSynchro": ["pullc"]
    }
    sweeper = sweep(parameters)
    return sweeper


def get_params_joined(parameter):
    (
        stressConso,
        idleConso,
        nameTechno,
        typeSynchro
    ) = (
        parameter["stressConso"],
        parameter["idleConso"],
        parameter["nameTechno"],
        parameter["typeSynchro"]
    )
    return f"{stressConso}-{idleConso}-{typeSynchro}-{nameTechno}"


def is_router(node_id, nb_nodes):
    return node_id == nb_nodes-1


def print_esds_node_results(results, api):
    s = f"--- Results {api.node_id} ---\n"
    for key, val in results.items():
        s += f"{key}: {val}\n"
    s += "-------------------------------"
    print(s)
