import json
import math
import os
from typing import List, Tuple

import yaml

from concerto_d_model.dependency_compute_model import DependencyComputeModel

# version_concerto_d = "sync"
# reconf_name = "update"
IMPLEM_OVERHEAD = 0.6


def _compute_esds_data_from_results(all_results):
    reconf_period_per_node = {}
    for node_result in all_results:
        node_id = node_result["node_id"]
        if node_id not in reconf_period_per_node.keys():
            reconf_period_per_node[node_id] = []

        reconf_period = {"connected_node_id": node_result["connected_node_id"], "dct": node_result["dct"], "type_dep": node_result["type_dep"], "reconf_period": []}
        for rp in node_result["trans_times"]:
            for _, period in rp.items():
                start, end = period.values()
                # if start != end:
                reconf_period["reconf_period"].append([start, end])
        reconf_period_per_node[node_id].append(reconf_period)
    return reconf_period_per_node


def _get_deploy_parallel_use_case_model(tts, nb_deps):
    t_sa = tts["server"]["t_sa"]
    t_scs = tts["server"]["t_sc"]
    t_sr = tts["server"]["t_sr"]

    ### Deploy
    configs = []
    services = []
    configs_names = []
    services_names = []
    for dep_num in range(nb_deps):
        config = DependencyComputeModel("provide", dep_num+1, None, [], [[tts[f"dep{dep_num}"]["t_di"]]])
        service = DependencyComputeModel("provide", dep_num+1, None, [[config]], [[tts[f"dep{dep_num}"]["t_dr"]]])
        configs.append(config)
        services.append(service)
        configs_names.append(f"config{dep_num}")
        services_names.append(f"service{dep_num}")

    # server
    in_intermediate = DependencyComputeModel("intermediate", 0, None, [], [[t_sa]])

    in_configs = []
    in_configs_names = []
    for dep_num in range(nb_deps):
        in_configs.append(DependencyComputeModel("use", 0, None, [[in_intermediate]], [[0]]))
        in_configs_names.append(f"in_config{dep_num}")

    # Ajout noeuds intermédiaires pour gérer les dépendances parallèles (pas un provide mais se calcul pareil)
    in_intermediate0 = DependencyComputeModel(
        "intermediate",
        0,
        None,
        [in_configs],
        [[t_scs[i]] for i in range(nb_deps)]
    )
    in_intermediate1 = DependencyComputeModel(
        "intermediate",
        0,
        None,
        [[in_intermediate0]],
        [[t_sr]]
    )

    in_services = []
    in_services_names = []
    for dep_num in range(nb_deps):
        in_services.append(DependencyComputeModel("use", 0, None, [[in_intermediate1]], [[0]]))
        in_services_names.append(f"in_service{dep_num}")

    for dep_num in range(nb_deps):
        configs[dep_num].connected_dep = in_configs[dep_num]
        in_configs[dep_num].connected_dep = configs[dep_num]

        services[dep_num].connected_dep = in_services[dep_num]
        in_services[dep_num].connected_dep = services[dep_num]

    return (
        configs + services + [in_intermediate] + in_configs + [in_intermediate0, in_intermediate1] + in_services,
        configs_names + services_names + ["in_intermediate"] + in_configs_names + ["in_intermediate0", "in_intermediate1"] + in_services_names
    )


def _get_update_parallel_use_case_model(tts, nb_deps):
    t_sr = tts["server"]["t_sr"]
    t_sss = tts["server"]["t_ss"]
    t_sps = tts["server"]["t_sp"]

    ### Update
    update_in_suspends = []
    update_services = []
    update_in_suspends_names = []
    update_services_names = []
    for dep_num in range(nb_deps):
        update_in_suspend = DependencyComputeModel("use", dep_num+1, None, [], [[0]])
        update_in_suspends.append(update_in_suspend)
        update_services.append(DependencyComputeModel("provide", dep_num+1, None, [[update_in_suspend]], [[tts[f"dep{dep_num}"]["t_du"] + tts[f"dep{dep_num}"]["t_dr"] + IMPLEM_OVERHEAD]]))
        update_in_suspends_names.append(f"update_in_suspend_{dep_num}")
        update_services_names.append(f"update_service_{dep_num}")

    # server
    update_out_suspends = []
    update_out_suspends_names = []
    for dep_num in range(nb_deps):
        update_out_suspends.append(DependencyComputeModel("provide", 0, None, [], [[t_sss[dep_num]]]))
        update_out_suspends_names.append(f"update_out_suspend_{dep_num}")

    intermediate_configured = DependencyComputeModel(
        "intermediate",
        0,
        None,
        [update_out_suspends],
        [[t_sps[i]] for i in range(nb_deps)]
    )

    update_in_configureds = []
    update_in_configureds_names = []
    for dep_num in range(nb_deps):
        update_in_configureds.append(DependencyComputeModel("use", 0, None, [[intermediate_configured]], [[0]]))
        update_in_configureds_names.append(f"update_in_configured_{dep_num}")

    wait_all_true = DependencyComputeModel("intermediate", 0, None, [update_in_configureds], [[0] for _ in range(nb_deps)])
    update_service = DependencyComputeModel("intermediate", 0, None, [[wait_all_true]], [[t_sr]])

    for dep_num in range(nb_deps):
        update_in_suspends[dep_num].connected_dep = update_out_suspends[dep_num]
        update_out_suspends[dep_num].connected_dep = update_in_suspends[dep_num]

        update_in_configureds[dep_num].connected_dep = update_services[dep_num]
        update_services[dep_num].connected_dep = update_in_configureds[dep_num]

    return (
        update_in_suspends + update_services + update_out_suspends + [intermediate_configured] + update_in_configureds + [wait_all_true, update_service],
        update_in_suspends_names + update_services_names + update_out_suspends_names + ["intermediate_configured"] + update_in_configureds_names + ["wait_all_true", "update_service"]
    )


def generate_mascots_schedules():
    print()
    print()
    dir_name = os.path.dirname(os.path.realpath(__file__))
    with open(f"{dir_name}/mascots_2023/mascots_expected.json") as f:
        expected = json.load(f)
    with open(f"{dir_name}/mascots_2023/mascots_struct.json") as f:
        results_dict = json.load(f)

    uptimes_schedules = {
        # "ud1_od0_15_25": json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud1_od0_15_25_perc.json")),
        # "ud2_od0_15_25": json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud2_od0_15_25_perc.json")),
        # "ud0_od1_15_25": json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od1_15_25_perc.json")),
        # "ud0_od2_15_25": json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od2_15_25_perc.json")),
        "ud0_od0_15_25": json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od0_15_25_perc-31_nodes.json")),
        "ud0_od0_7_25": json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od0_7_25_perc-31_nodes.json")),
        "ud0_od0_30_25": json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od0_30_25_perc-31_nodes.json")),
    }
    # ud1_od0_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud1_od0_15_25_perc.json"))
    # ud2_od0_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud2_od0_15_25_perc.json"))
    # ud0_od1_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od1_15_25_perc.json"))
    # ud0_od2_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od2_15_25_perc.json"))
    #
    # ud0_od0_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od0_15_25_perc-31_nodes.json"))
    # ud0_od0_7_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od0_7_25_perc-31_nodes.json"))
    # ud0_od0_30_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od0_30_25_perc-31_nodes.json"))

    # for nb_deps in [1, 2, 3, 4, 5]:
    for nb_deps in [5, 10, 20, 30]:
        i = 0
        print(f"Generating for nb_deps: {nb_deps}...")
        # for uptime_schedule in [ud0_od0_15_25, ud1_od0_15_25, ud2_od0_15_25, ud0_od1_15_25, ud0_od2_15_25, ud0_od0_7_25, ud0_od0_30_25]:
        # for uptime_schedule in [ud0_od0_15_25, ud0_od0_7_25, ud0_od0_30_25]:
        for name_uptime, uptime_schedule_nodes in uptimes_schedules.items():
            for version_concerto_d in ["sync", "async"]:
                for reconf_name in ["deploy", "update"]:
                    for trans_times in ["T0", "T1"]:
                        for type_synchro in ["pull"]:
                            with open(f"/home/aomond/concerto-d-projects/experiment_files/parameters/transitions_times/transitions_times-1-30-deps12-{trans_times[1:]}.json") as f:
                                tts = json.load(f)["transitions_times"]

                            uptime_schedule = uptime_schedule_nodes[:nb_deps+1]

                            # print(name_uptime, version_concerto_d, reconf_name, trans_times)
                            if reconf_name == "deploy":
                                list_deps, name_deps = _get_deploy_parallel_use_case_model(tts, nb_deps)
                            else:
                                list_deps, name_deps = _get_update_parallel_use_case_model(tts, nb_deps)

                            for dep in list_deps:
                                dep.nodes_schedules = uptime_schedule

                            m = 0
                            j = 0

                            # Create result dict for 1 server and 5 deps
                            all_results_esds = []
                            sum_reconf_duration = 0
                            for dep in list_deps:
                                dct, result_dep = dep.compute_time(version_concerto_d, type_synchro)
                                # print(dep.node_id, name_deps[j], dct, result_dep)
                                connected_node_id = dep.connected_dep.node_id if dep.type_dep in ["provide", "use"] else None
                                all_results_esds.append({"node_id": dep.node_id, "connected_node_id": connected_node_id, "name_dep": name_deps[j], "type_dep": dep.type_dep, "dct": dct, "trans_times": result_dep})
                                if dct > m:
                                    m = dct

                                for res in result_dep:
                                    for val in res.values():
                                        start, end = val["start"], val["end"]
                                        sum_reconf_duration += end - start

                                # print(name_deps[j], dct, result_dep)
                                j += 1
                            # for dep in [self.in_config0, self.in_config1, self.in_config2, self.in_config3, self.in_config4,
                            #             self.in_service0, self.in_service1, self.in_service2, self.in_service3, self.in_service4]:
                            #     dct, result_dep = dep.compute_time()

                            # TODO: retirer le temps du début sur toute la reconf et pas uniquement ici
                            offset_start = min(uptime_schedule, key=lambda s: s[0][0] if s[0][0] != -1 else math.inf)[0][0]
                            m_time = m - offset_start
                            # print(f"removed {offset_start}")
                            exp_val = expected[name_uptime][version_concerto_d][reconf_name][trans_times]
                            delta_s = m_time - exp_val
                            delta_perc = delta_s*100/exp_val
                            if trans_times == "T0":
                                if reconf_name == "deploy":
                                    expected_reconf_duration = 111.75
                                else:
                                    expected_reconf_duration = 73.96 + IMPLEM_OVERHEAD
                            else:
                                if reconf_name == "deploy":
                                    expected_reconf_duration = 91.23
                                else:
                                    expected_reconf_duration = 100.24 + IMPLEM_OVERHEAD

                            result_str = f"max {trans_times} {reconf_name} {version_concerto_d} {name_uptime}: {m_time}s, delta: {round(delta_s, 2)}s - {round(delta_perc, 2)}% ({exp_val}s expe). Sum reconf: {round(sum_reconf_duration, 2)} ({round(expected_reconf_duration, 2)} expected)"
                            if abs(delta_perc) > 1:
                                result_str = result_str + "#############################################"
                            if nb_deps == 5:
                                results_dict[name_uptime][version_concerto_d][reconf_name][trans_times] = {nb_deps: result_str}

                            # Generate ESDS configuration
                            esds_data = _compute_esds_data_from_results(all_results_esds)

                            ## Uptime periods
                            uptimes_periods_per_node = _compute_uptimes_periods_per_node(uptime_schedule, m_time)
                            router_key = nb_deps+1

                            ## Reconf periods
                            reconf_periods_per_node = _compute_reconf_periods_per_node(esds_data)
                            merged_reconf_periods_per_node = {node_id: count_active_intervals(interval_list) for node_id, interval_list in reconf_periods_per_node.items()}

                            ## Requests periods
                            sending_periods_per_node = _compute_sending_periods_per_node(esds_data)
                            merged_sending_periods_per_node = {node_id: count_active_intervals_sending(interval_list) for node_id, interval_list in sending_periods_per_node.items()}
                            sending_periods_during_uptime_per_node = _compute_sending_periods_during_uptime_per_node(uptimes_periods_per_node, merged_sending_periods_per_node)

                            ## Responses periods
                            receive_periods_per_node = _compute_receive_periods_from_sending_periods(sending_periods_per_node)
                            merged_receive_periods_per_node = {node_id: count_active_intervals_sending(interval_list) for node_id, interval_list in receive_periods_per_node.items()}
                            receive_periods_during_uptime_per_node = _compute_sending_periods_during_uptime_per_node(uptimes_periods_per_node, merged_receive_periods_per_node)
                            # overlaps_periods_per_dep = _compute_uses_overlaps_with_provide(uptimes_periods_per_node)
                            # receive_periods_during_uptime_per_node = _compute_sending_periods_during_uptime_per_node(overlaps_periods_per_dep, merged_receive_periods_per_node)

                            ## Router periods
                            if version_concerto_d == "async":
                                ### Uptimes
                                router_uptimes_periods = _compute_router_uptimes_periods(uptimes_periods_per_node)
                                uptimes_periods_per_node[router_key] = router_uptimes_periods

                                ### Receive
                                all_receive_periods = []
                                for receive_periods in receive_periods_per_node.values():
                                    all_receive_periods.extend(receive_periods)
                                router_receive_periods = {router_key: count_active_intervals_sending(all_receive_periods)}
                                router_receive_periods_during_uptime = _compute_sending_periods_during_uptime_per_node(uptimes_periods_per_node, router_receive_periods)
                                receive_periods_during_uptime_per_node.update(router_receive_periods_during_uptime)
                            else:
                                uptimes_periods_per_node[router_key] = []
                                receive_periods_during_uptime_per_node[router_key] = []

                            merged_reconf_periods_per_node[router_key] = []
                            sending_periods_during_uptime_per_node[router_key] = []

                            # Expe parameters file
                            title = f"esds_generated_data-{name_uptime}-{version_concerto_d}-{reconf_name}-{trans_times}-{nb_deps}-{type_synchro}"
                            expe_parameters = {
                                "title": title,
                                "nb_nodes": nb_deps + 2,
                                "uptimes_periods_per_node": uptimes_periods_per_node,
                                "reconf_periods_per_node": merged_reconf_periods_per_node,
                                "sending_periods_per_node": sending_periods_during_uptime_per_node,
                                "receive_periods_per_node": receive_periods_during_uptime_per_node,
                                "max_execution_duration": m
                            }

                            expe_esds_parameter_files = f"/home/aomond/reconfiguration-esds/concerto-d-results/expe_esds_parameter_files_to_compute"
                            os.makedirs(expe_esds_parameter_files, exist_ok=True)
                            with open(os.path.join(expe_esds_parameter_files, f"{title}.yaml"), "w") as f:
                                yaml.safe_dump(expe_parameters, f)

                            # # Verification file
                            # verification = {"max_execution_duration": m, "reconf_periods": {}, "sending_periods": {}, "receive_periods": {}}
                            # ## Reconf
                            # for node_id, reconf_periods in merged_reconf_periods_per_node.items():
                            #     verification["reconf_periods"][node_id] = sum((end - start) * nb_processes for start, end, nb_processes in reconf_periods)
                            # ## Send
                            # for node_id, sending_periods in merged_sending_periods_per_node.items():
                            #     verification["sending_periods"][node_id] = _compute_sending_periods_per_connected_node(node_id, sending_periods, uptime_schedule)
                            # ## Receive
                            # for node_id, receive_periods in merged_receive_periods_per_node.items():
                            #     verification["receive_periods"][node_id] = _compute_sending_periods_per_connected_node(node_id, receive_periods, uptime_schedule)
                            #
                            # ## Write file
                            # expe_esds_verification_files = f"/home/aomond/reconfiguration-esds/concerto-d-results/expe_esds_verification_files"
                            # os.makedirs(expe_esds_verification_files, exist_ok=True)
                            # with open(os.path.join(expe_esds_verification_files, f"{title}.yaml"), "w") as f:
                            #     yaml.safe_dump(verification, f)
            i += 1

    print(json.dumps(results_dict, indent=4))


def _compute_uses_overlaps_with_provide(uptimes_periods_per_node):
    overlaps_periods = {node_id: {} for node_id in uptimes_periods_per_node.keys()}
    for node_id, node_uptimes in uptimes_periods_per_node.items():
        for provide_up_start, provide_up_end in node_uptimes:
            for remote_node_id, remote_node_uptimes in uptimes_periods_per_node.items():
                if node_id != remote_node_id:
                    for remote_up_start, remote_up_end in remote_node_uptimes:
                        if remote_node_id not in overlaps_periods[node_id].keys():
                            overlaps_periods[node_id][remote_node_id] = []
                        if min(provide_up_end, remote_up_end) - max(provide_up_start, remote_up_start) > 0:
                            overlaps_periods[node_id][remote_node_id].append([max(provide_up_start, remote_up_start), min(provide_up_end, remote_up_end)])
    return overlaps_periods


def _compute_router_uptimes_periods(uptimes_periods_per_node):
    flatten_uptimes_periods = []
    for periods in uptimes_periods_per_node.values():
        flatten_uptimes_periods.extend(periods)
    flatten_uptimes_periods.sort(key=lambda period: period[0])  # Sort by start time

    if len(flatten_uptimes_periods) == 0:
        return []

    first_start, first_end = flatten_uptimes_periods[0]
    router_uptimes = [[first_start, first_end]]
    for start, end in flatten_uptimes_periods[1:]:
        last_start, last_end = router_uptimes[-1]
        if start > last_end:
            router_uptimes.append([start, end])
        else:
            router_uptimes[-1] = [last_start, max(end, last_end)]

    return router_uptimes


def test_compute_router_uptimes_periods():
    uptimes_periods_per_node_0 = {
        0: [[10, 20]],
        1: [[5, 30], [40, 60]],
    }
    uptimes_periods_per_node_1 = {
        0: [[0, 10], [100, 150]],
        1: [[5, 20], [40, 60]],
        2: [[7, 8], [15, 25]],
        3: [[25, 40]]
    }
    assert _compute_router_uptimes_periods(uptimes_periods_per_node_0) == [[5, 30], [40, 60]]
    assert _compute_router_uptimes_periods(uptimes_periods_per_node_1) == [[0, 60], [100, 150]]


def _compute_sending_periods_during_uptime_per_node(uptimes_nodes, sending_periods):
    result = {node_id: [] for node_id in sending_periods.keys()}
    for node_id, periods in sending_periods.items():
        for start_period, end_period, send_nodes in periods:
            for start_uptime, end_uptime in uptimes_nodes[node_id]:
                if start_period < end_uptime and end_period > start_uptime:
                    result[node_id].append([max(start_uptime, start_period), min(end_period, end_uptime), send_nodes])
    return result


def _compute_receive_periods_from_overlaps_per_node(overlaps_nodes, sending_periods):
    result = {node_id: [] for node_id in sending_periods.keys()}
    for node_id, periods in sending_periods.items():
        for start_period, end_period, send_nodes in periods:
            for remote_id, nb_send in send_nodes.items():
                for start_uptime, end_uptime in overlaps_nodes[node_id][remote_id]:
                    if start_period < end_uptime and end_period > start_uptime:
                        result[node_id].append([max(start_uptime, start_period), min(end_period, end_uptime), send_nodes])
    return result


def test_compute_sending_periods_during_uptime_per_node():
    uptimes = [
        [[0, 50], [100, 150], [300, 350]],
        [[0, 50], [100, 150], [300, 350]],
        [[0, 50], [100, 150], [300, 350]],
    ]
    s_p_0 = {0: [[60, 70, {1: 1}]]}
    s_p_1 = {0: [[10, 20.5, {2: 2}]]}
    s_p_2 = {0: [[30.5, 115.5, {3: 1}]]}
    s_p_3 = {0: [[25.3, 340.2, {5: 1, 6: 2}]]}
    s_p_4 = {0: [[70.1, 410.3, {7: 4}]], 1: [[150, 300, {}]], 2: [[300, 350, {}]]}

    assert _compute_sending_periods_during_uptime_per_node(uptimes, s_p_0) == {0: []}
    assert _compute_sending_periods_during_uptime_per_node(uptimes, s_p_1) == {0: [[10, 20.5, {2: 2}]]}
    assert _compute_sending_periods_during_uptime_per_node(uptimes, s_p_2) == {0: [[30.5, 50, {3: 1}], [100, 115.5, {3: 1}]]}
    assert _compute_sending_periods_during_uptime_per_node(uptimes, s_p_3) == {
        0: [[25.3, 50, {5: 1, 6: 2}], [100, 150, {5: 1, 6: 2}], [300, 340.2, {5: 1, 6: 2}]]
    }
    assert _compute_sending_periods_during_uptime_per_node(uptimes, s_p_4) == {
        0: [[100, 150, {7: 4}], [300, 350, {7: 4}]],
        1: [],
        2: [[300, 350, {}]]
    }


def _compute_uptimes_periods_per_node(uptime_schedule, m_time: float):
    uptimes_periods_per_node = {node_id: [] for node_id in range(len(uptime_schedule))}
    for node_id, node_schedule in enumerate(uptime_schedule):
        for uptime, _ in node_schedule:
            if uptime != -1 and uptime < m_time:
                uptime_end = min(uptime + 50, m_time)  # TODO magic value
                uptimes_periods_per_node[node_id].append([uptime, uptime_end])
                if uptime + 50 >= m_time:
                    break

    return uptimes_periods_per_node


def _compute_sending_periods_per_connected_node(node_id, sending_periods, uptime_schedule):
    sending_periods_per_connected_node = {}
    for uptime, _ in uptime_schedule[node_id]:
        if uptime != -1:
            uptime_end = uptime + 50  # TODO magic value
            for start_send, end_send, count_sends in sending_periods:
                if count_sends != {} and start_send < uptime_end and end_send >= uptime:
                    for conn_id, count in count_sends.items():
                        period_amount = (min(end_send, uptime_end) - max(start_send, uptime)) * count
                        if conn_id not in sending_periods_per_connected_node.keys():
                            sending_periods_per_connected_node[conn_id] = period_amount
                        else:
                            sending_periods_per_connected_node[conn_id] += period_amount
    return sending_periods_per_connected_node


def _compute_receive_periods_from_sending_periods(sending_periods_per_node):
    receive_periods_per_node = {node_id: [] for node_id in sending_periods_per_node.keys()}
    for sender_id, sending_periods in sending_periods_per_node.items():
        for receiver_id, start_send, end_send in sending_periods:
            receive_periods_per_node[receiver_id].append([sender_id, start_send, end_send])

    # Sort lists by start_send
    for node_id, receive_periods in receive_periods_per_node.items():
        receive_periods_per_node[node_id] = sorted(receive_periods, key=lambda period: period[1])

    return receive_periods_per_node


def count_active_intervals(interval_list):
    # Create set with all interval start and end
    s = set()
    for start, end in interval_list:
        s.add(start)
        s.add(end)
    endpoints = sorted(s)

    # Between each endpoints, count the number of interval included
    result = []
    for i in range(len(endpoints) - 1):
        start = endpoints[i]
        end = endpoints[i + 1]

        count = 0
        for i_start, i_end in interval_list:
            if start >= i_start and end <= i_end:
                count += 1

        result.append([start, end, count])

    return result


def count_active_intervals_sending(interval_list):
    # TODO: refacto with count_active_intervals method (merge)
    # Create set with all interval start and end
    s = set()
    for _, start, end in interval_list:
        s.add(start)
        s.add(end)
    endpoints = sorted(s)

    # Between each endpoints, count the number of interval included
    result = []
    for i in range(len(endpoints) - 1):
        start = endpoints[i]
        end = endpoints[i + 1]

        count = {}
        for connected_node_id, i_start, i_end in interval_list:
            if start >= i_start and end <= i_end:
                if connected_node_id not in count.keys():
                    count[connected_node_id] = 1
                else:
                    count[connected_node_id] += 1

        result.append([start, end, count])

    return result


def _compute_reconf_periods_per_node(esds_data):
    result = {}

    # Flatten reconf_periods and sort by starting period
    for node_id, node_values in esds_data.items():
        result[node_id] = []
        for node_value in node_values:
            for start, end in node_value["reconf_period"]:
                if start != end:
                    result[node_id].append([start, end])
        result[node_id] = sorted(result[node_id], key=lambda item: item[0])

    return result


def _compute_sending_periods_per_node(esds_data):
    result = {}

    for node_id, node_values in esds_data.items():
        result[node_id] = []
        for node_value in node_values:
            connected_node_id = node_value["connected_node_id"]
            if connected_node_id is not None:
                start_sending = max(period[1] for period in node_value["reconf_period"])
                end_sending = node_value["dct"]

                result[node_id].append([connected_node_id, start_sending, end_sending])
        result[node_id] = sorted(result[node_id], key=lambda item: item[2])

    return result


if __name__ == "__main__":
    generate_mascots_schedules()
