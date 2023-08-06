import yaml
from esds.plugins.power_states import PowerStatesComms

FREQUENCE_POLLING = 1
NB_POLL_PER_SEC = 10


def sending(api, type_comm):
    node_id = api.node_id % api.args["nodes_per_batch"]

    # Init
    with open(api.args["expe_config_file"]) as f:
        expe_config = yaml.safe_load(f)

        # Check if nb_deps is crossed
        nb_deps = expe_config["nb_deps"]
        if node_id not in [0, 6] and node_id > nb_deps:
            return

        title = expe_config["title"]
        node_uptimes = expe_config["uptimes_periods_per_node"][node_id]
        sending_periods_per_node = expe_config[f"{type_comm}_periods_per_node"][node_id]
        max_execution_duration = expe_config["max_execution_duration"]

    # Version concerto_d parameters
    if "async" not in title:
        interface_name = f"eth0"
    else:
        interface_name = f"eth0Router"
    commsConso = api.args["commsConso"]
    api.log(f"Interface: {interface_name}")
    tot_sending_time_flat, tot_no_sending_time_flat = 0, 0
    sending_cons = PowerStatesComms(api)
    sending_cons.set_power(interface_name, 0, commsConso, commsConso)

    size = 257
    api.turn_off()
    for up_start, up_end in node_uptimes:
        # Sleeping period (no receive)
        wait_before_start = up_start - api.read("clock")
        api.log(f"Waiting {wait_before_start} before starting")
        api.wait(wait_before_start)

        # Uptime period
        api.turn_on()
        for start, end, node_send in sending_periods_per_node:
            # Search sending periods of the current uptime
            if node_send != {} and up_start <= start and end <= up_end:
                # No sending period
                no_sending_period = start - api.read("clock")
                api.log(f"Wait {no_sending_period} until next period")
                api.wait(no_sending_period)
                tot_no_sending_time_flat += no_sending_period

                # Sending period
                api.log("Start sending")
                sending_start = api.read("clock")
                while api.read("clock") < end:
                    for sender_id, count in node_send.items():
                        if api.read("clock") < end:
                            end_period = end - api.read("clock")
                            data_to_send = size * count * NB_POLL_PER_SEC
                            api.sendt(interface_name, (node_id, sender_id), data_to_send, sender_id, timeout=end_period)
                    if api.read("clock") < end:
                        api.wait(min(FREQUENCE_POLLING, end - api.read("clock")))
                tot_sending_time_flat += api.read("clock") - sending_start

        remaining_uptime = up_end - api.read("clock")
        api.log(f"Waiting remaining uptime {remaining_uptime}")
        api.wait(remaining_uptime)
        tot_no_sending_time_flat += remaining_uptime

        # Sleeping period
        api.turn_off()
    remaining_no_sending_duration = max_execution_duration - api.read("clock")
    api.log(f"Waiting {remaining_no_sending_duration} before terminating")
    api.wait(remaining_no_sending_duration)
    sending_cons_energy = sending_cons.get_energy()

    results = {
        f"tot_{type_comm}_flat_time": tot_sending_time_flat,
        f"tot_no_{type_comm}_time": round(tot_no_sending_time_flat, 2),
        "node_conso": 0,
        "comms_cons": float(round(sending_cons_energy, 2)),
    }
    print_esds_node_results(results, api)
    results_categ = "sends" if type_comm == "sending" else "receives"
    with open(f"/home/aomond/reconfiguration-esds/concerto-d-results/results/{results_categ}/{title}/{node_id}.yaml", "w") as f:
        yaml.safe_dump(results, f)


def get_simulation_swepped_parameters():
    """
    Source of truth of parameters
    :return:
    """
    from execo_engine import sweep

    parameters = {
        "stressConso": [0, 1.20],
        "idleConso": [1.38],
        "techno": [{"name": "lora", "bandwidth": "50kbps", "commsConso": 0.16},
                   {"name": "nbiot", "bandwidth": "200kbps", "commsConso": 0.65}],
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
        parameter["techno"]["name"],
        parameter["typeSynchro"]
    )
    return f"{stressConso}-{idleConso}-{nameTechno}-{typeSynchro}"


def print_esds_node_results(results, api):
    s = f"--- Results {api.node_id} ---\n"
    for key, val in results.items():
        s += f"{key}: {val}\n"
    s += "-------------------------------"
    print(s)
