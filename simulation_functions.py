from esds.node import Node
from esds.plugins.power_states import PowerStates, PowerStatesComms

OFF_POWER = 0
ON_POWER = 0.4
PROCESS_POWER = 1  # TODO model energetic
LORA_POWER = 0.16

NB_NODES = 6


def execution_work(api, node_uptimes, work_periods_per_node, max_execution_duration, type_process):
    duration = 50
    interface_name = "eth0"

    # Start expe
    ### Setup node power consumption
    node_cons = PowerStates(api, 0)
    comms_cons = None
    if type_process != "reconf":
        comms_cons = PowerStatesComms(api)
        comms_cons.set_power(interface_name, 0, LORA_POWER, LORA_POWER)

    ### Run expe
    api.turn_off()
    node_cons.set_power(OFF_POWER)
    tot_working_time_dict = {}  # For sending
    tot_working_time_flat_dict = {}  # For sending
    tot_working_time = 0
    tot_working_flat_time = 0
    tot_no_working_time = 0
    tot_sleeping_time = 0
    sleep_start = 0

    def c():
        return api.read("clock")

    for i in range(len(node_uptimes)):
        uptime, _ = node_uptimes[i]
        if uptime != -1:
            # Off period
            sleeping_time = min(uptime, max_execution_duration) - c()
            api.log(f"Sleeping for: {round(sleeping_time, 2)}s")
            api.wait(sleeping_time)
            tot_sleeping_time += c() - sleep_start

            # On period
            ## No working period
            api.turn_on()
            uptime_end = uptime + duration

            if type_process == "reconf":
                tot_no_working_time, tot_working_flat_time, tot_working_time = _handle_reconf(
                    api, c, i, node_cons,
                    node_uptimes,
                    work_periods_per_node,
                    tot_no_working_time,
                    tot_working_flat_time,
                    tot_working_time, uptime,
                    uptime_end
                )
            elif type_process in ["sending", "receive"]:
                tot_no_working_time, tot_working_time_dict, tot_working_time_flat_dict = _handle_sending(
                    api, c, work_periods_per_node, uptime, uptime_end, tot_working_time_dict, tot_working_time_flat_dict, tot_no_working_time, type_process
                )

            ## No reconf period, wait until sleeping
            remaining_waiting_duration = min(uptime_end, max_execution_duration) - c()
            if remaining_waiting_duration > 0:
                api.log(f"End of uptime period in: {round(remaining_waiting_duration, 2)}s")
                tot_no_working_time += remaining_waiting_duration
                api.wait(remaining_waiting_duration)
            else:
                api.log(f"End of uptime period already reached since {abs(remaining_waiting_duration)}s, sleeping immediately")

            # Off period
            api.turn_off()
            node_cons.set_power(OFF_POWER)
            sleep_start = c()
            if c() >= max_execution_duration:
                api.log(f"Threshold reached: {max_execution_duration}s. End of choreography")
                break

    # Whether not to print energy
    tot_comms_cons = 0 if type_process == "reconf" else comms_cons.get_energy()
    return tot_working_time, tot_working_flat_time, tot_no_working_time, tot_sleeping_time, tot_working_time_dict, tot_working_time_flat_dict, node_cons.energy, tot_comms_cons


def _handle_reconf(
        api, c, i, node_cons, node_uptimes, work_periods_per_node,
        tot_no_working_time, tot_working_flat_time, tot_working_time, uptime, uptime_end
):
    ## Compute next uptime start. Execute all actions duration with nb_processes > 0 until this
    j = i + 1
    next_uptime_start = node_uptimes[j][0] if j < len(node_uptimes) else uptime_end
    while j < len(node_uptimes) and next_uptime_start == -1:
        next_uptime_start = node_uptimes[j][0]
        j += 1
    node_cons.set_power(ON_POWER)
    for start, end, nb_processes in work_periods_per_node:
        if nb_processes > 0 and uptime <= start < next_uptime_start:
            ## No reconf period
            wait_before_reconf_start = max(start, c()) - c()
            api.log(f"Waiting for action start: {round(wait_before_reconf_start, 2)}s")
            tot_no_working_time += wait_before_reconf_start
            api.wait(wait_before_reconf_start)

            ## Reconf period
            node_cons.set_power(ON_POWER + nb_processes * PROCESS_POWER)  # TODO model energetic
            action_duration = end - start
            api.log(f"Action duration: {round(action_duration, 2)}")
            api.wait(action_duration)
            tot_working_time += (end - start) * nb_processes
            tot_working_flat_time += end - start

            ## No reconf period
            node_cons.set_power(ON_POWER)
        else:
            api.log(f"Skipping reconf_periods: [{start}, {end}, {nb_processes}], current uptime: {uptime}, next uptime: {next_uptime_start}")
    return tot_no_working_time, tot_working_flat_time, tot_working_time


def _handle_sending(api: Node, c, work_periods_per_node, uptime, uptime_end, tot_working_time_dict, tot_working_time_flat_dict, tot_no_working_time, type_process):
    for start_send, end_send, count_sends in work_periods_per_node:
        if count_sends != {} and start_send < uptime_end and end_send >= uptime:
            ## No sending period
            wait_before_sending_start = max(start_send, c()) - c()
            api.log(f"Waiting for sending to start: {round(wait_before_sending_start, 2)}s")
            tot_no_working_time += wait_before_sending_start
            api.wait(wait_before_sending_start)

            ## Sending period
            bandwidth = 1  # 1Bps (set on platform.yaml) TODO: take it into account in the calcul
            tot_weight_send = sum(count_sends.values())
            sending_end = min(end_send, uptime_end)
            sending_duration = sending_end - c()  # Nodes need to send continuously during this period
            datasize = round(sending_duration / tot_weight_send, 3)  # Fraction the send window by the weight of the send
            api.log(f"Sending duration: {sending_duration}. Datasize: {datasize}. tot_weight_send: {tot_weight_send}. Bandwidth: {bandwidth}. Sending start: {c()}. Sending end: {sending_end}")
            for conn_id, weight_send in count_sends.items():
                ## Each node send a msg in a fraction of the total sending_duration
                api.log(f"Start sending {weight_send} sized packets to {conn_id}")
                datasize_to_send = datasize*weight_send
                nb_nodes = NB_NODES if type_process == "send" else NB_NODES * 2   # If receive, add an additionnal NB_NODES
                api.sendt("eth0", "Msg", datasize_to_send, conn_id + nb_nodes, timeout=datasize_to_send)
                api.log("End sending")

                ## Register the total time spend sending data per receiver id
                if conn_id not in tot_working_time_dict.keys():
                    tot_working_time_dict[conn_id] = datasize_to_send
                else:
                    tot_working_time_dict[conn_id] += datasize_to_send

                ## Register theoretical weighted duration during which packets are continuously sent to a receiver
                ## Do not represent the real working duration. It serves for verification purposes.
                if conn_id not in tot_working_time_flat_dict.keys():
                    tot_working_time_flat_dict[conn_id] = sending_duration*weight_send
                else:
                    tot_working_time_flat_dict[conn_id] += sending_duration*weight_send
        else:
            api.log(f"Skipping sending_period: [{start_send}, {end_send}, {count_sends}], current uptime {uptime}")

    return tot_no_working_time, tot_working_time_dict, tot_working_time_flat_dict
