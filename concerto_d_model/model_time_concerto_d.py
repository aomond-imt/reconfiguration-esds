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


def _get_deploy_parallel_use_case_model(tts):
    t_sa = tts["server"]["t_sa"]
    t_scs = tts["server"]["t_sc"]
    t_sr = tts["server"]["t_sr"]

    ### Deploy
    # dep0
    config0 = DependencyComputeModel("provide", 1, None, [], [[tts["dep0"]["t_di"]]])
    service0 = DependencyComputeModel("provide", 1, None, [[config0]], [[tts["dep0"]["t_dr"]]])

    # dep1
    config1 = DependencyComputeModel("provide", 2, None, [], [[tts["dep1"]["t_di"]]])
    service1 = DependencyComputeModel("provide", 2, None, [[config1]], [[tts["dep1"]["t_dr"]]])

    # dep2
    config2 = DependencyComputeModel("provide", 3, None, [], [[tts["dep2"]["t_di"]]])
    service2 = DependencyComputeModel("provide", 3, None, [[config2]], [[tts["dep2"]["t_dr"]]])

    # dep3
    config3 = DependencyComputeModel("provide", 4, None, [], [[tts["dep3"]["t_di"]]])
    service3 = DependencyComputeModel("provide", 4, None, [[config3]], [[tts["dep3"]["t_dr"]]])

    # dep4
    config4 = DependencyComputeModel("provide", 5, None, [], [[tts["dep4"]["t_di"]]])
    service4 = DependencyComputeModel("provide", 5, None, [[config4]], [[tts["dep4"]["t_dr"]]])

    # server
    in_intermediate = DependencyComputeModel("intermediate", 0, None, [], [[t_sa]])
    in_config0 = DependencyComputeModel("use", 0, None, [[in_intermediate]], [[0]])
    in_config1 = DependencyComputeModel("use", 0, None, [[in_intermediate]], [[0]])
    in_config2 = DependencyComputeModel("use", 0, None, [[in_intermediate]], [[0]])
    in_config3 = DependencyComputeModel("use", 0, None, [[in_intermediate]], [[0]])
    in_config4 = DependencyComputeModel("use", 0, None, [[in_intermediate]], [[0]])

    # Ajout noeuds intermédiaires pour gérer les dépendances parallèles (pas un provide mais se calcul pareil)
    in_intermediate0 = DependencyComputeModel(
        "intermediate",
        0,
        None,
        [[in_config0, in_config1, in_config2, in_config3, in_config4]],
        [[t_scs[0]], [t_scs[1]], [t_scs[2]], [t_scs[3]], [t_scs[4]]]
    )
    in_intermediate1 = DependencyComputeModel(
        "intermediate",
        0,
        None,
        [[in_intermediate0]],
        [[t_sr]]
    )

    in_service0 = DependencyComputeModel("use", 0, None, [[in_intermediate1]], [[0]])
    in_service1 = DependencyComputeModel("use", 0, None, [[in_intermediate1]], [[0]])
    in_service2 = DependencyComputeModel("use", 0, None, [[in_intermediate1]], [[0]])
    in_service3 = DependencyComputeModel("use", 0, None, [[in_intermediate1]], [[0]])
    in_service4 = DependencyComputeModel("use", 0, None, [[in_intermediate1]], [[0]])

    config0.connected_dep = in_config0
    in_config0.connected_dep = config0
    config1.connected_dep = in_config1
    in_config1.connected_dep = config1
    config2.connected_dep = in_config2
    in_config2.connected_dep = config2
    config3.connected_dep = in_config3
    in_config3.connected_dep = config3
    config4.connected_dep = in_config4
    in_config4.connected_dep = config4

    service0.connected_dep = in_service0
    in_service0.connected_dep = service0
    service1.connected_dep = in_service1
    in_service1.connected_dep = service1
    service2.connected_dep = in_service2
    in_service2.connected_dep = service2
    service3.connected_dep = in_service3
    in_service3.connected_dep = service3
    service4.connected_dep = in_service4
    in_service4.connected_dep = service4

    return [
        config0, config1, config2, config3, config4, service0, service1, service2, service3,
        service4, in_intermediate, in_config0, in_config1, in_config2, in_config3,
        in_config4, in_intermediate0, in_intermediate1, in_service0, in_service1, in_service2,
        in_service3, in_service4
    ], ["config0", "config1", "config2", "config3", "config4", "service0", "service1", "service2", "service3",
        "service4", "in_intermediate", "in_config0", "in_config1", "in_config2", "in_config3", "in_config4",
        "in_intermediate0", "in_intermediate1",
        "in_service0", "in_service1", "in_service2",
        "in_service3", "in_service4"
    ]


def _get_update_parallel_use_case_model(tts):
    t_sr = tts["server"]["t_sr"]
    t_sss = tts["server"]["t_ss"]
    t_sps = tts["server"]["t_sp"]

    ### Update
    # dep0
    update_in_suspend_0 = DependencyComputeModel("use", 1, None, [], [[0]])
    update_service_0 = DependencyComputeModel("provide", 1, None, [[update_in_suspend_0]], [[tts["dep0"]["t_du"] + tts["dep0"]["t_dr"]]])

    # dep1
    update_in_suspend_1 = DependencyComputeModel("use", 2, None, [], [[0]])
    update_service_1 = DependencyComputeModel("provide", 2, None, [[update_in_suspend_1]], [[tts["dep1"]["t_du"] + tts["dep1"]["t_dr"] + IMPLEM_OVERHEAD]])

    # dep2
    update_in_suspend_2 = DependencyComputeModel("use", 3, None, [], [[0]])
    update_service_2 = DependencyComputeModel("provide", 3, None, [[update_in_suspend_2]], [[tts["dep2"]["t_du"] + tts["dep2"]["t_dr"]]])

    # dep3
    update_in_suspend_3 = DependencyComputeModel("use", 4, None, [], [[0]])
    update_service_3 = DependencyComputeModel("provide", 4, None, [[update_in_suspend_3]], [[tts["dep3"]["t_du"] + tts["dep3"]["t_dr"]]])

    # dep4
    update_in_suspend_4 = DependencyComputeModel("use", 5, None, [], [[0]])
    update_service_4 = DependencyComputeModel("provide", 5, None, [[update_in_suspend_4]], [[tts["dep4"]["t_du"] + tts["dep4"]["t_dr"]]])

    # server
    update_out_suspend_0 = DependencyComputeModel("provide", 0, None, [], [[t_sss[0]]])
    update_out_suspend_1 = DependencyComputeModel("provide", 0, None, [], [[t_sss[1]]])
    update_out_suspend_2 = DependencyComputeModel("provide", 0, None, [], [[t_sss[2]]])
    update_out_suspend_3 = DependencyComputeModel("provide", 0, None, [], [[t_sss[3]]])
    update_out_suspend_4 = DependencyComputeModel("provide", 0, None, [], [[t_sss[4]]])

    intermediate_configured = DependencyComputeModel(
        "intermediate",
        0,
        None,
        [[update_out_suspend_0, update_out_suspend_1, update_out_suspend_2, update_out_suspend_3, update_out_suspend_4]],
        [[t_sps[0]], [t_sps[1]], [t_sps[2]], [t_sps[3]], [t_sps[4]]]
    )
    update_in_configured_0 = DependencyComputeModel("use", 0, None, [[intermediate_configured]], [[0]])
    update_in_configured_1 = DependencyComputeModel("use", 0, None, [[intermediate_configured]], [[0]])
    update_in_configured_2 = DependencyComputeModel("use", 0, None, [[intermediate_configured]], [[0]])
    update_in_configured_3 = DependencyComputeModel("use", 0, None, [[intermediate_configured]], [[0]])
    update_in_configured_4 = DependencyComputeModel("use", 0, None, [[intermediate_configured]], [[0]])
    wait_all_true = DependencyComputeModel("intermediate", 0, None, [[update_in_configured_0, update_in_configured_1, update_in_configured_2, update_in_configured_3, update_in_configured_4]], [[0], [0], [0], [0], [0]])
    update_service = DependencyComputeModel("intermediate", 0, None, [[wait_all_true]], [[t_sr]])

    update_in_suspend_0.connected_dep = update_out_suspend_0
    update_out_suspend_0.connected_dep = update_in_suspend_0
    update_in_suspend_1.connected_dep = update_out_suspend_1
    update_out_suspend_1.connected_dep = update_in_suspend_1
    update_in_suspend_2.connected_dep = update_out_suspend_2
    update_out_suspend_2.connected_dep = update_in_suspend_2
    update_in_suspend_3.connected_dep = update_out_suspend_3
    update_out_suspend_3.connected_dep = update_in_suspend_3
    update_in_suspend_4.connected_dep = update_out_suspend_4
    update_out_suspend_4.connected_dep = update_in_suspend_4

    update_in_configured_0.connected_dep = update_service_0
    update_service_0.connected_dep = update_in_configured_0
    update_in_configured_1.connected_dep = update_service_1
    update_service_1.connected_dep = update_in_configured_1
    update_in_configured_2.connected_dep = update_service_2
    update_service_2.connected_dep = update_in_configured_2
    update_in_configured_3.connected_dep = update_service_3
    update_service_3.connected_dep = update_in_configured_3
    update_in_configured_4.connected_dep = update_service_4
    update_service_4.connected_dep = update_in_configured_4

    return [
        update_in_suspend_0, update_service_0, update_in_suspend_1, update_service_1, update_in_suspend_2,
        update_service_2, update_in_suspend_3, update_service_3, update_in_suspend_4, update_service_4, update_out_suspend_0,
        update_out_suspend_1, update_out_suspend_2, update_out_suspend_3, update_out_suspend_4, intermediate_configured,
        update_in_configured_0, update_in_configured_1, update_in_configured_2, update_in_configured_3, update_in_configured_4,
        wait_all_true, update_service
    ], [
        "update_in_suspend_0", "update_service_0", "update_in_suspend_1", "update_service_1", "update_service_2",
        "update_in_suspend_2", "update_in_suspend_3", "update_service_3", "update_in_suspend_4", "update_service_4", "update_out_suspend_0",
        "update_out_suspend_1", "update_out_suspend_2", "update_out_suspend_3", "update_out_suspend_4", "intermediate_configured",
        "update_in_configured_0", "update_in_configured_1", "update_in_configured_2", "update_in_configured_3", "update_in_configured_4",
        "wait_all_true", "update_service"
    ]


def generate_mascots_schedules():
    print()
    print()
    dir_name = os.path.dirname(os.path.realpath(__file__))
    with open(f"{dir_name}/mascots_2023/mascots_expected.json") as f:
        expected = json.load(f)
    with open(f"{dir_name}/mascots_2023/mascots_struct.json") as f:
        results_dict = json.load(f)

    ud0_od0_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od0_15_25_perc.json"))
    ud1_od0_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud1_od0_15_25_perc.json"))
    ud2_od0_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud2_od0_15_25_perc.json"))
    ud0_od1_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od1_15_25_perc.json"))
    ud0_od2_15_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od2_15_25_perc.json"))
    ud0_od0_7_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od0_7_25_perc.json"))
    ud0_od0_30_25 = json.load(open("/home/aomond/concerto-d-projects/experiment_files/parameters/uptimes/mascots_uptimes-60-50-5-ud0_od0_30_25_perc.json"))

    i = 0
    for uptime_schedule in [ud0_od0_15_25, ud1_od0_15_25, ud2_od0_15_25, ud0_od1_15_25, ud0_od2_15_25,
                            ud0_od0_7_25, ud0_od0_30_25]:
        for version_concerto_d in ["sync", "async"]:
            for reconf_name in ["deploy", "update"]:
                for trans_times in ["T0", "T1"]:

                    name_uptime = [*expected.keys()][i]
                    with open(f"/home/aomond/concerto-d-projects/experiment_files/parameters/transitions_times/transitions_times-1-30-deps12-{trans_times[1:]}.json") as f:
                        tts = json.load(f)["transitions_times"]

                    # print(name_uptime, version_concerto_d, reconf_name, trans_times)
                    if reconf_name == "deploy":
                        list_deps, name_deps = _get_deploy_parallel_use_case_model(tts)
                    else:
                        list_deps, name_deps = _get_update_parallel_use_case_model(tts)

                    for dep in list_deps:
                        dep.nodes_schedules = uptime_schedule

                    m = 0
                    j = 0

                    # Create result dict for 1 server and 5 deps
                    all_results_esds = []
                    sum_reconf_duration = 0
                    for dep in list_deps:
                        dct, result_dep = dep.compute_time(version_concerto_d)
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
                    exp_val = [*expected.values()][i][version_concerto_d][reconf_name][trans_times]
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
                    results_dict[name_uptime][version_concerto_d][reconf_name][trans_times] = result_str

                    # Generate ESDS configuration
                    esds_data = _compute_esds_data_from_results(all_results_esds)

                    ## Uptime periods
                    uptimes_periods_per_node = _compute_uptimes_periods_per_node(uptime_schedule, m_time)
                    router_key = max(uptimes_periods_per_node.keys()) + 1

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

                    ## Router periods
                    router_uptimes_periods = _compute_router_uptimes_periods(uptimes_periods_per_node)
                    uptimes_periods_per_node[router_key] = router_uptimes_periods
                    merged_reconf_periods_per_node[router_key] = []
                    sending_periods_during_uptime_per_node[router_key] = []
                    receive_periods_during_uptime_per_node[router_key] = []

                    # Expe parameters file
                    title = f"esds_generated_data-{name_uptime}-{version_concerto_d}-{reconf_name}-{trans_times}"
                    expe_parameters = {
                        "title": title,
                        "uptimes_nodes": uptime_schedule,
                        "uptimes_periods_per_node": uptimes_periods_per_node,
                        "reconf_periods_per_node": merged_reconf_periods_per_node,
                        "sending_periods_per_node": sending_periods_during_uptime_per_node,
                        "receive_periods_per_node": receive_periods_during_uptime_per_node,
                        "max_execution_duration": m
                    }

                    expe_esds_parameter_files = "/tmp/expe_esds_parameter_files"
                    os.makedirs(expe_esds_parameter_files, exist_ok=True)
                    with open(os.path.join(expe_esds_parameter_files, f"{title}.yaml"), "w") as f:
                        yaml.safe_dump(expe_parameters, f)

                    # Verification file
                    verification = {"max_execution_duration": m, "reconf_periods": {}, "sending_periods": {}, "receive_periods": {}}
                    ## Reconf
                    for node_id, reconf_periods in merged_reconf_periods_per_node.items():
                        verification["reconf_periods"][node_id] = sum((end - start) * nb_processes for start, end, nb_processes in reconf_periods)
                    ## Send
                    for node_id, sending_periods in merged_sending_periods_per_node.items():
                        verification["sending_periods"][node_id] = _compute_sending_periods_per_connected_node(node_id, sending_periods, uptime_schedule)
                    ## Receive
                    for node_id, receive_periods in merged_receive_periods_per_node.items():
                        verification["receive_periods"][node_id] = _compute_sending_periods_per_connected_node(node_id, receive_periods, uptime_schedule)

                    ## Write file
                    expe_esds_verification_files = "/tmp/expe_esds_verification_files"
                    os.makedirs(expe_esds_verification_files, exist_ok=True)
                    with open(os.path.join(expe_esds_verification_files, f"{title}.yaml"), "w") as f:
                        yaml.safe_dump(verification, f)
        i += 1

    print(json.dumps(results_dict, indent=4))


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
    # TODO: handle overlaps
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
    # TODO: handle overlaps
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
