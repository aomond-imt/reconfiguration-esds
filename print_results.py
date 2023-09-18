import collections
import copy
import itertools
import json
import os

import yaml
import ujson
import numpy as np
import matplotlib.pyplot as plt


def _gather_results(global_results_stats, conso_name):
    gathered_results_acc = {}
    for key, nodes_results in global_results_stats.items():
        for num_run in range(len(nodes_results["time"])):
            router_id = max(nodes_results["energy"]["idles"].keys())
            energy_results = nodes_results["energy"]
            if key not in gathered_results_acc.keys():
                gathered_results_acc[key] = {num_run: {"energy": {}, "time": nodes_results["time"][num_run]}}
            else:
                gathered_results_acc[key][num_run] = {"energy": {}, "time": nodes_results["time"][num_run]}

            # filter_tot = ["idles", "reconfs", "sendings", "receives"]
            if conso_name == "static":
                filter_tot = ["idles", "reconfs", "sendings", "receives"]
            else:
                filter_tot = ["reconfs", "sendings", "receives"]
            for node_id in sorted(energy_results["idles"].keys()):
                tot = 0
                s = {"idles": 0, "reconfs": 0, "sendings": 0, "receives": 0}
                for name in s.keys():
                    s[name] += energy_results[name][node_id]["node_conso"][num_run] + energy_results[name][node_id]["comms_cons"][num_run]
                    # if name in filter_tot or node_id == router_id:
                    if name in filter_tot:
                        tot += s[name]
                # s.update({
                #     "tot_msg_sent": energy_results["sendings"][node_id]["tot_msg_sent"][num_run],
                #     "tot_ack_received": energy_results["sendings"][node_id]["tot_ack_received"][num_run],
                #     "tot_wait_polling": energy_results["sendings"][node_id]["tot_wait_polling"][num_run],
                #     "tot_msg_received": energy_results["receives"][node_id]["tot_msg_received"][num_run],
                #     "tot_msg_responded": energy_results["receives"][node_id]["tot_msg_responded"][num_run]
                # })

                gathered_results_acc[key][num_run]["energy"][node_id] = {"tot": round(tot, 2), "detail": s}
                # print(f"{node_id}: {round(tot, 2)}J --- Detail: {s}")
    return gathered_results_acc


def print_energy_results(global_results, conso_name):
    print(" ------------ Results --------------")
    gathered_results = _gather_results(global_results, conso_name)

    for key, vals in gathered_results.items():
        print(key)
        for node_id, res in vals["energy"].items():
            print(f"{node_id}: {round(res['tot'], 2)}J --- Detail: {res['detail']}")
        print(f"time: {vals['time']}s")
    print("------------------------------------")


def _group_by_version_concerto_d(gathered_results):
    grouped_results = {}
    for key, res in gathered_results.items():
        version = "async" if "async" in key else "sync"
        key_without_version = "-".join(key.split(f"-{version}-"))
        if key_without_version not in grouped_results.keys():
            grouped_results[key_without_version] = {version: res}
        else:
            grouped_results[key_without_version][version] = res

    return grouped_results


def analyse_energy_results(global_results, conso_name):
    print(" ------------ Results --------------")
    gathered_results = _gather_results(global_results, conso_name)
    group_by_version_concerto_d = _group_by_version_concerto_d(gathered_results)
    for key, vals in group_by_version_concerto_d.items():
        sum_reconf_sync = 0
        sum_sending_sync = 0
        sum_reconf_async = 0
        sum_sending_async = 0
        print(key)
        if "sync" in vals.keys():
            print("sync")
            for node_id, res_energy in vals["sync"]["energy"].items():
                print(f"{node_id}: {round(res_energy['tot'], 2)}J --- Detail: {res_energy['detail']}")
                sum_reconf_sync += res_energy['detail']['reconfs']
                sum_sending_sync += res_energy['detail']['sendings'] + res_energy['detail']['receives']
            print(f"Ratio reconf/sending: {sum_reconf_sync:.2f}/{sum_sending_sync:.2f} ({sum_reconf_sync/sum_sending_sync:.2f})")
        if "async" in vals.keys():
            print("async")
            for node_id, res_energy in vals["async"]["energy"].items():
                print(f"{node_id}: {round(res_energy['tot'], 2)}J --- Detail: {res_energy['detail']}")
                sum_reconf_async += res_energy['detail']['reconfs']
                sum_sending_async += res_energy['detail']['sendings'] + res_energy['detail']['receives']
            print(f"Ratio reconf/sending: {sum_reconf_async:.2f}/{sum_sending_async:.2f} ({sum_reconf_async / sum_sending_async:.2f})")


def compute_energy_gain(global_results_accumulated, conso_name):
    gathered_results = _gather_results(global_results_accumulated, conso_name)
    group_by_version_concerto_d = _group_by_version_concerto_d(gathered_results)
    all_results = {}
    for key, vals in group_by_version_concerto_d.items():
        if "async" not in vals.keys() or "sync" not in vals.keys():
            print(f"{key}: Async or sync missing, skip")
            continue

        for num_run in range(min(len(vals["sync"]), len(vals["async"]))):
            router_id = max(vals["async"][num_run]["energy"].keys())
            assert router_id == max(vals["sync"][num_run]["energy"].keys())
            if key not in all_results.keys():
                all_results[key] = {num_run: {}}
            else:
                all_results[key][num_run] = {}
            tot_ons_sync = 0
            tot_ons_async = 0
            tot_router = 0
            tot_detail = {}
            for name in ["detail_ons_sync", "detail_ons_async", "detail_router"]:
                tot_detail[name] = {"idles": 0, "reconfs": 0, "sendings": 0, "receives": 0}

            for vals_sync, vals_async in zip(vals["sync"][num_run]["energy"].items(), vals["async"][num_run]["energy"].items()):
                node_id, node_results_sync = vals_sync
                _, node_results_async = vals_async
                tot_gain = node_results_async["tot"] - node_results_sync["tot"]
                if node_id == router_id:
                    tot_router = node_results_async["tot"]
                else:
                    tot_ons_sync += node_results_sync["tot"]
                    tot_ons_async += node_results_async["tot"]
                all_results[key][num_run][node_id] = {"gain": round(tot_gain, 2), "sync": node_results_sync['tot'], "async": node_results_async['tot']}
                all_results[key][num_run][node_id]["details"] = {}
                for detail_sync, detail_async in zip(node_results_sync["detail"].items(), node_results_async["detail"].items()):
                    name, val_sync = detail_sync
                    name_a, val_async = detail_async
                    assert name == name_a
                    if name not in ["idles", "reconfs", "sendings", "receives"]:
                        continue
                    gain = val_async - val_sync
                    all_results[key][num_run][node_id]["details"][name] = {"gain": round(gain, 2), "sync": val_sync, "async": val_async}

                    if node_id < router_id:
                        tot_detail["detail_ons_sync"][name] += val_sync
                        tot_detail["detail_ons_async"][name] += val_async
                    else:
                        tot_detail["detail_router"][name] += val_async

            all_results[key][num_run]["total"] = {
                "sync": round(tot_ons_sync, 2),
                "async_no_router": round(tot_ons_async, 2),
                "async_with_router": round(tot_ons_async + tot_router, 2),
                "gain_no_router": round((tot_ons_sync - tot_ons_async) * 100 / tot_ons_sync, 2) if tot_ons_sync != 0 else "NA",
                "gain_with_router": round((tot_ons_sync - (tot_ons_async+tot_router)) * 100 / tot_ons_sync, 2) if tot_ons_sync != 0 else "NA",
                "time_sync": vals["sync"][num_run]["time"],
                "time_async": vals["async"][num_run]["time"],
                "gain_time": round((vals["sync"][num_run]["time"] - vals["async"][num_run]["time"]) * 100 / vals["sync"][num_run]["time"], 2)
            }
            all_results[key][num_run]["total"].update(tot_detail)

    return all_results


def print_energy_gain(energy_gain):
    for key, vals in energy_gain.items():
        print(key)
        for element, values in vals.items():
            if element != "total":
                print(f"{element}: tot_gain: {values['gain']}J (sync: {values['sync']}J, async: {values['async']}J)", end=" - ")
                for name, val in values["details"].items():
                    print(f"{name}: {round(val['gain'], 2)}J (sync: {val['sync']}J, async: {val['async']}J)", end=", ")
                print()
            else:
                print(f"Total ONs sync: {values['sync']}J")
                print(f"Total ONs async no router: {values['async_no_router']}J")
                print(f"Total ONs async with router: {values['async_with_router']}J")
                print(f"Gain ONs using async (no router) {values['gain_no_router']}%")
                print(f"Gain system using async (with router) {values['gain_with_router']}%")
                print()


def compute_energy_gain_by_nb_deps(energy_gains):
    energy_gain_by_nb_deps = {}
    for key, val in energy_gains.items():
        scenario = "-".join(key.split("-")[:-3])
        if scenario not in energy_gain_by_nb_deps.keys():
            energy_gain_by_nb_deps[scenario] = {}
        nb_deps = int(key.split("-")[7:][0])
        if nb_deps not in energy_gain_by_nb_deps[scenario]:
            energy_gain_by_nb_deps[scenario][nb_deps] = val

    # for key, val in energy_gain_by_nb_deps.items():
    #     energy_gain_by_nb_deps[key] = {}
    #     for scenario, values in val:
    #         nb_deps = scenario.split("-")[-2]
    #         energy_gain_by_nb_deps[key][nb_deps] = values
    sorted_deps = collections.OrderedDict(sorted(energy_gain_by_nb_deps.items()))
    for key, vals in sorted_deps.items():
        sorted_deps[key] = collections.OrderedDict(sorted(vals.items()))
    return sorted_deps


def compute_energy_gain_by_uptime_durations(energy_gains_by_nb_deps):
    energy_gains_by_uptime_durations = {}
    for key, val in energy_gains_by_nb_deps.items():
        uptime_duration = key.split("-")[3]
        scenario = key.replace(f"-{uptime_duration}-sec", "")
        if scenario not in energy_gains_by_uptime_durations:
            energy_gains_by_uptime_durations[scenario] = {int(uptime_duration): val}
        else:
            energy_gains_by_uptime_durations[scenario][int(uptime_duration)] = val

    sorted_uptimes_durations = collections.OrderedDict(sorted(energy_gains_by_uptime_durations.items()))
    for key, vals in sorted_uptimes_durations.items():
        sorted_uptimes_durations[key] = collections.OrderedDict(sorted(vals.items()))
    return sorted_uptimes_durations


def plot_scatter_results(energy_gain_by_nb_deps, param_names):
    color_num = 0
    fig, ax = plt.subplots()
    colors = [
        'tab:blue',
        'tab:orange',
        'tab:green',
        'tab:red',
        'tab:purple',
        'tab:brown',
        'tab:pink',
        'tab:gray',
        'tab:olive',
        'tab:cyan',
        '#DCDCDC',
        '#000000',
    ]

    for scenario_name, gain_by_nb_deps in energy_gain_by_nb_deps.items():
        gains_energy_list = []
        gains_time_list = []
        sizes = []
        for nb_dep, gains in gain_by_nb_deps.items():
            gains_energy_list.append(gains["total"]["gain_with_router"])
            gains_time_list.append(gains["total"]["gain_time"])
            sizes.append(int(nb_dep) * 5)
        scatter = ax.scatter(gains_time_list, gains_energy_list, c=colors[color_num], label=scenario_name.replace("esds_generated_data-ud0_od0_","").replace("_25", ""), s=sizes)
        handles, labels = scatter.legend_elements(prop="sizes", alpha=0.6, func=lambda x: x//5)
        legend1 = ax.legend(handles, labels, title="Nb deps", loc=(1.04, 0.7))
        ax.add_artist(legend1)
        color_num += 1

    ax.set_xlabel("% Time variation")
    ax.set_ylabel("% Energy variation")
    ax.legend(loc=(1.04, 0))
    ax.axvline(0, c='black', ls='--')
    ax.axhline(0, c='black', ls='--')
    ax.set_title(param_names)
    plt.subplots_adjust(right=0.75)
    plt.show()


def plot_surface_results(energy_gain_by_nb_deps, param_names):
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    for i in range(3):
        ax.bar([1, 2, 3, 4, 5], [4*i, 5*i + 3, 6*i], zs=[10+i], zdir="y", color=["r", "g", "b"])
    plt.show()


def _compute_elements_and_bottom(uptime_duration, gain_by_nb_deps):
    elements = {
        "sync": {
            "ons": [el["total_stats"]["sync"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_ons_idles": [el["total_stats"]["detail_ons_sync"]["idles"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_ons_reconfs": [el["total_stats"]["detail_ons_sync"]["reconfs"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_ons_sendings": [el["total_stats"]["detail_ons_sync"]["sendings"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_ons_receives": [el["total_stats"]["detail_ons_sync"]["receives"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
            "time_sync": [el["total_stats"]["time_sync"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
        },
        "async": {
            "ons": [el["total_stats"]["async_with_router"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],  # TODO: check for the mean of the router entry
            "detail_ons_idles": [el["total_stats"]["detail_ons_async"]["idles"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_ons_reconfs": [el["total_stats"]["detail_ons_async"]["reconfs"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_ons_sendings": [el["total_stats"]["detail_ons_async"]["sendings"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_ons_receives": [el["total_stats"]["detail_ons_async"]["receives"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
            # "router": [el["total_stats"]["async_with_router"] - el["total_stats"]["async_no_router"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_router_idles": [el["total_stats"]["detail_router"]["idles"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_router_reconfs": [el["total_stats"]["detail_router"]["reconfs"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_router_sendings": [el["total_stats"]["detail_router"]["sendings"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_router_receives": [el["total_stats"]["detail_router"]["receives"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
            "time_async": [el["total_stats"]["time_async"]["mean"] for el in gain_by_nb_deps[uptime_duration].values()],
        },
    }
    stds = {
        "sync": {
            "ons": [el["total_stats"]["sync"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_ons_idles": [el["total_stats"]["detail_ons_sync"]["idles"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_ons_reconfs": [el["total_stats"]["detail_ons_sync"]["reconfs"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_ons_sendings": [el["total_stats"]["detail_ons_sync"]["sendings"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_ons_receives": [el["total_stats"]["detail_ons_sync"]["receives"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
            "time_sync": [el["total_stats"]["time_sync"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
        },
        "async": {
            "ons": [el["total_stats"]["async_with_router"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],  # TODO: check for the mean of the router entry
            "detail_ons_idles": [el["total_stats"]["detail_ons_async"]["idles"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_ons_reconfs": [el["total_stats"]["detail_ons_async"]["reconfs"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_ons_sendings": [el["total_stats"]["detail_ons_async"]["sendings"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_ons_receives": [el["total_stats"]["detail_ons_async"]["receives"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
            # "router": [el["total_stats"]["async_with_router"] - el["total_stats"]["async_no_router"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_router_idles": [el["total_stats"]["detail_router"]["idles"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_router_reconfs": [el["total_stats"]["detail_router"]["reconfs"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_router_sendings": [el["total_stats"]["detail_router"]["sendings"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
            "detail_router_receives": [el["total_stats"]["detail_router"]["receives"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
            "time_async": [el["total_stats"]["time_async"]["std"] for el in gain_by_nb_deps[uptime_duration].values()],
        },
    }
    bottom = {
        "sync": np.zeros(len(gain_by_nb_deps[uptime_duration].keys())),
        "async": np.zeros(len(gain_by_nb_deps[uptime_duration].keys())),
    }

    return elements, bottom, stds


def plot_bar_results(energy_gain_by_uptime_durations, param_names):
    print("Starting plotting")
    for type_reconf in ["sync", "async"]:
        print(f"Type reconf: {type_reconf}")
        for scenario_name, gain_by_uptime_durations in energy_gain_by_uptime_durations.items():
            print(f"Creating plot for: {scenario_name}")
            # scenario_name = 'esds_generated_data-ud0_od0_30_25-deploy-T0'
            # gain_by_uptime_durations = energy_gain_by_nb_deps[scenario_name]
            if 60 in gain_by_uptime_durations.keys():
                x = np.arange(len(gain_by_uptime_durations[60].keys())) * 2
            elif 120 in gain_by_uptime_durations.keys():
                x = np.arange(len(gain_by_uptime_durations[120].keys())) * 2
            else:
                x = np.arange(len(gain_by_uptime_durations[180].keys())) * 2
            # print(json.dumps(elements, indent=2))
            elements_per_ud = {}
            bottom_per_ud = {}
            stds = {}
            for ud in gain_by_uptime_durations.keys():
                elements_per_ud[ud], bottom_per_ud[ud], stds[ud] = _compute_elements_and_bottom(ud, gain_by_uptime_durations)
            # elements, bottom = _compute_elements_and_bottom(uptime_duration, gain_by_uptime_durations)

            # fig, ax = plt.subplots()
            fig, ax = plt.subplots(figsize=(10, 10))
            multiplier = 0
            width = 0.4
            max_bound = 0
            for ud in gain_by_uptime_durations.keys():
                for attribute, measurement in elements_per_ud[ud].items():
                    if attribute == type_reconf:
                        offset = width * multiplier
                        max_bound = _plot_tot(attribute, ax, bottom_per_ud[ud], max_bound, measurement, offset, width, x, stds[ud])
                        # max_bound = _plot_detail(attribute, ax, bottom_per_ud[ud], max_bound, measurement, offset, width, x, ud)
                        # max_bound = _plot_tot_time(attribute, ax, bottom_per_ud[ud], max_bound, measurement, offset, width, x)
                        multiplier += 1

            ax.set_ylabel('Energy (J)')
            ax.set_xlabel('Nb deps')

            scenario, _ = scenario_name.replace("esds_generated_data-uptimes-dao-", "").split("-")
            action_conso, idle_conso, _, type_techno = param_names.split("-")
            # title = f'{scenario_name}-{param_names}'.replace("esds_generated_data-uptimes-dao-", "").replace("-", "   ")
            rn_presence_text = "With RN" if type_reconf == "async" else "Without RN"
            title = f'Dynamic energy\n{rn_presence_text}\nScenario: {scenario} - Dynamic action conso: {action_conso} - Static idle conso: {idle_conso} - Type techno: {type_techno}'

            ax.set_title(title)
            if 60 in gain_by_uptime_durations.keys():
                ax.set_xticks(x + width, gain_by_uptime_durations[60].keys())
            elif 120 in gain_by_uptime_durations.keys():
                ax.set_xticks(x + width, gain_by_uptime_durations[120].keys())
            else:
                ax.set_xticks(x + width, gain_by_uptime_durations[180].keys())

            ax.legend(loc='upper left', ncols=3, borderaxespad=0.)
            # if type_reconf == "async":
            #     if "update" in scenario_name:
            #         ax.set_ylim(0, 700)      # Dynamic
            #         # ax.set_ylim(0, 36000)  # Static
            #     else:
            #         ax.set_ylim(0, 550)      # Dynamic
            #         # ax.set_ylim(0, 30000)    # Static
            # else:
            #     if "update" in scenario_name:
            #         ax.set_ylim(0, 1800)     # Dynamic
            #         # ax.set_ylim(0, 280000) # Static
            #     else:
            #         ax.set_ylim(0, 2000)     # Dynamic
            #         # ax.set_ylim(0, 650000) # Static
            ax.set_ylim(0, max_bound * 1.4)

            # plt.show()
            dir_to_save = f"{os.environ['HOME']}/results-reconfiguration-esds/results-greencom/graphs"
            # dir_to_save = f"{os.environ['HOME']}/reconfiguration-esds/concerto-d-results/pycharm_plots/detail/{param_names}"
            os.makedirs(dir_to_save, exist_ok=True)
            plt.savefig(f"{dir_to_save}/dynamic-{type_reconf}-{scenario_name}-{param_names}.png")


def _plot_tot(attribute, ax, bottom, max_bound, measurement, offset, width, x, stds):
    if attribute == "sync":
        rects = ax.bar(x + offset, measurement["ons"], width, bottom=bottom[attribute], label=attribute, yerr=stds[attribute]["ons"])
        bottom[attribute] = bottom[attribute] + measurement["ons"]
        ax.bar_label(rects, padding=3)
        max_bound = max(max_bound, max(bottom[attribute]))
    elif attribute == "async":
        rects = ax.bar(x + offset, measurement["ons"], width, bottom=bottom[attribute], label="async (ons)", yerr=stds[attribute]["ons"])
        bottom[attribute] = bottom[attribute] + measurement["ons"]
        # ax.bar_label(rects, padding=3)
        # rects = ax.bar(x + offset, measurement["router"], width, bottom=bottom[attribute], label="async (router)")
        # bottom[attribute] = bottom[attribute] + measurement["router"]
        ax.bar_label(rects, padding=3)
        max_bound = max(max_bound, max(bottom[attribute]))
    return max_bound


def _plot_tot_time(attribute, ax, bottom, max_bound, measurement, offset, width, x):
    if attribute == "sync":
        rects = ax.bar(x + offset, measurement["time_sync"], width, bottom=bottom[attribute], label=attribute)
        bottom[attribute] = bottom[attribute] + measurement["time_sync"]
        # ax.bar_label(rects, padding=3, fmt=lambda val: f"{round(val/3600, 2)} ({round(val/3600/24, 2)}jours)s")
        ax.bar_label(rects, padding=3, fmt=lambda val: f"{round(val/3600/24, 2)}j")
        max_bound = max(max_bound, max(bottom[attribute]))
    elif attribute == "async":
        rects = ax.bar(x + offset, measurement["time_async"], width, bottom=bottom[attribute], label="async (ons)")
        bottom[attribute] = bottom[attribute] + measurement["time_async"]
        # ax.bar_label(rects, padding=3, fmt=lambda val: f"{round(val/3600, 2)} ({round(val/3600/24, 2)}jours)s")
        ax.bar_label(rects, padding=3, fmt=lambda val: f"{round(val/3600/24, 2)}j")
        max_bound = max(max_bound, max(bottom[attribute]))
    return max_bound


def _plot_detail(attribute, ax, bottom, max_bound, measurement, offset, width, x, ud):
    if attribute == "sync":
        # rects = ax.bar(x + offset, measurement["detail_ons_idles"], width, bottom=bottom[attribute], label="sync ons (idles)")
        # bottom[attribute] = bottom[attribute] + measurement["detail_ons_idles"]
        rects = ax.bar(x + offset, measurement["detail_ons_reconfs"], width, bottom=bottom[attribute], label=f"sync ons (reconfs) ({ud})")
        bottom[attribute] = bottom[attribute] + measurement["detail_ons_reconfs"]
        # ax.bar_label(rects, padding=3)
        rects = ax.bar(x + offset, measurement["detail_ons_sendings"], width, bottom=bottom[attribute], label="sync ons (requests)")
        bottom[attribute] = bottom[attribute] + measurement["detail_ons_sendings"]
        # ax.bar_label(rects, padding=3)
        rects = ax.bar(x + offset, measurement["detail_ons_receives"], width, bottom=bottom[attribute], label="sync ons (responses)")
        bottom[attribute] = bottom[attribute] + measurement["detail_ons_receives"]
        ax.bar_label(rects, padding=3)
        max_bound = max(max_bound, max(bottom[attribute]))
    elif attribute == "async":
        # rects = ax.bar(x + offset, measurement["detail_ons_idles"], width, bottom=bottom[attribute], label="async ons (idles)")
        # bottom[attribute] = bottom[attribute] + measurement["detail_ons_idles"]
        # ax.bar_label(rects, padding=3)
        rects = ax.bar(x + offset, measurement["detail_ons_reconfs"], width, bottom=bottom[attribute], label=f"async ons (reconfs) ({ud})")
        bottom[attribute] = bottom[attribute] + measurement["detail_ons_reconfs"]
        # ax.bar_label(rects, padding=3)
        rects = ax.bar(x + offset, measurement["detail_ons_sendings"], width, bottom=bottom[attribute], label="async ons (requests)")
        bottom[attribute] = bottom[attribute] + measurement["detail_ons_sendings"]
        # ax.bar_label(rects, padding=3)
        rects = ax.bar(x + offset, measurement["detail_ons_receives"], width, bottom=bottom[attribute], label="async ons (responses)")
        bottom[attribute] = bottom[attribute] + measurement["detail_ons_receives"]
        # ax.bar_label(rects, padding=3)
        # rects = ax.bar(x + offset, measurement["detail_router_idles"], width, bottom=bottom[attribute], label="async router (idles)")
        # bottom[attribute] = bottom[attribute] + measurement["detail_router_idles"]
        # ax.bar_label(rects, padding=3)
        rects = ax.bar(x + offset, measurement["detail_router_sendings"], width, bottom=bottom[attribute], label="async router (requests)")
        bottom[attribute] = bottom[attribute] + measurement["detail_router_sendings"]
        # ax.bar_label(rects, padding=3)
        rects = ax.bar(x + offset, measurement["detail_router_receives"], width, bottom=bottom[attribute], label="async router (responses)")
        bottom[attribute] = bottom[attribute] + measurement["detail_router_receives"]
        ax.bar_label(rects, padding=3)
        max_bound = max(max_bound, max(bottom[attribute]))
    return max_bound


def accumulate_global_results(all_global_results):
    scenarios = set()
    for global_results in all_global_results.values():
        if len(scenarios) == 0:
            scenarios = set(global_results.keys())
        else:
            scenarios = scenarios.intersection(global_results.keys())

    global_results_accumulated = {}
    for scenario_acc in scenarios:
        # global_results_accumulated[scenario_acc] =
        results_acc = {
            "time": [],
            "energy": {}
        }

        for global_results in all_global_results.values():
            for scenario_res, vals in global_results.items():
                if scenario_acc == scenario_res:
                    results_acc["time"].append(vals["time"])
                    for type_e in ["idles", "receives", "reconfs", "sendings"]:
                        for str_node_num, vals_e in vals["energy"][type_e].items():
                            node_num = int(str_node_num)
                            if type_e not in results_acc["energy"].keys():
                                results_acc["energy"][type_e] = {node_num: {"comms_cons": [vals_e["comms_cons"]], "node_conso": [vals_e["node_conso"]]}}
                            else:
                                if node_num not in results_acc["energy"][type_e].keys():
                                    results_acc["energy"][type_e][node_num] = {"comms_cons": [vals_e["comms_cons"]], "node_conso": [vals_e["node_conso"]]}
                                else:
                                    results_acc["energy"][type_e][node_num]["comms_cons"].append(vals_e["comms_cons"])
                                    results_acc["energy"][type_e][node_num]["node_conso"].append(vals_e["node_conso"])
        global_results_accumulated[scenario_acc] = results_acc

    # global_results_stats = {}
    # for scenario, values in global_results_accumulated.items():
    #     global_results_stats[scenario] = {
    #         "time": {"mean": np.mean(values["time"]), "std": np.std(values["time"])},
    #         "energy": {
    #             type_conso: {
    #                 node_id: {
    #                         name_conso: {"mean": np.mean(vals[name_conso]), "std": np.std(vals[name_conso]), "min": np.min(vals[name_conso]), "max": np.max(vals[name_conso])
    #                     } for name_conso in ["comms_cons", "node_conso"]
    #                 } for node_id, vals in values["energy"][type_conso].items()
    #             } for type_conso in ["idles", "receives", "reconfs", "sendings"]
    #         }
    #     }

    return global_results_accumulated


def _compute_stats_energy_gains(energy_gain_by_uptime_durations, conso_name):
    energy_gain_by_uptime_durations_mean_std = copy.deepcopy(energy_gain_by_uptime_durations)
    type_consos = ["idles", "reconfs", "sendings", "receives"]
    for scenario, ud_values in energy_gain_by_uptime_durations.items():
        for ud, nb_deps_values in ud_values.items():
            for nb_deps, run_values in nb_deps_values.items():
                sync_vals = []
                async_no_router_vals = []
                async_with_router_vals = []
                gains_energy = []
                gains_time = []
                gains_sync_energy_60_ud = []
                gains_async_energy_60_ud = []
                gains_sync_time_60_ud = []
                gains_async_time_60_ud = []
                time_sync_vals = []
                time_async_vals = []
                detail_ons_sync = {"idles": [], "reconfs": [], "sendings": [], "receives": [], "comms": []}
                detail_ons_async = {"idles": [], "reconfs": [], "sendings": [], "receives": [], "comms": []}
                detail_router = {"idles": [], "reconfs": [], "sendings": [], "receives": [], "comms": []}

                for num_run, node_values in run_values.items():
                    sync_vals.append(node_values["total"]["sync"])
                    async_no_router_vals.append(node_values["total"]["async_no_router"])
                    async_with_router_vals.append(node_values["total"]["async_with_router"])
                    gains_energy.append((node_values["total"]["sync"] - node_values["total"]["async_with_router"])*100/node_values["total"]["sync"])
                    gains_time.append((node_values["total"]["time_sync"] - node_values["total"]["time_async"])*100/node_values["total"]["time_sync"])
                    ud_60_stats = ud_values[60][nb_deps][num_run]
                    g_s_e_60_ud = (ud_60_stats["total"]["sync"]-node_values["total"]["sync"])*100/ud_60_stats["total"]["sync"]
                    g_as_e_60_ud = (ud_60_stats["total"]["async_with_router"]-node_values["total"]["async_with_router"])*100/ud_60_stats["total"]["async_with_router"]
                    g_s_t_60_ud = (ud_60_stats["total"]["time_sync"]-node_values["total"]["time_sync"])*100/ud_60_stats["total"]["time_sync"]
                    g_as_t_60_ud = (ud_60_stats["total"]["time_async"]-node_values["total"]["time_async"])*100/ud_60_stats["total"]["time_async"]
                    gains_sync_energy_60_ud.append(g_s_e_60_ud)
                    gains_async_energy_60_ud.append(g_as_e_60_ud)
                    gains_sync_time_60_ud.append(g_s_t_60_ud)
                    gains_async_time_60_ud.append(g_as_t_60_ud)
                    time_sync_vals.append(node_values["total"]["time_sync"])
                    time_async_vals.append(node_values["total"]["time_async"])
                    for type_conso in type_consos:
                        detail_ons_sync[type_conso].append(node_values["total"]["detail_ons_sync"][type_conso])
                        detail_ons_async[type_conso].append(node_values["total"]["detail_ons_async"][type_conso])
                        detail_router[type_conso].append(node_values["total"]["detail_router"][type_conso])

                    detail_ons_sync["comms"].append(node_values["total"]["detail_ons_sync"]["sendings"] + node_values["total"]["detail_ons_sync"]["receives"])
                    detail_ons_async["comms"].append(node_values["total"]["detail_ons_async"]["sendings"] + node_values["total"]["detail_ons_async"]["receives"])
                    detail_router["comms"].append(node_values["total"]["detail_router"]["sendings"] + node_values["total"]["detail_router"]["receives"])

                unit = 1000 if conso_name == "static" else 1
                unit_str = "kJ" if conso_name == "static" else "J"
                energy_gain_by_uptime_durations_mean_std[scenario][ud][nb_deps]["total_stats"] = {
                    "sync": {"mean": f"{round(np.mean(sync_vals)/unit, 2)}{unit_str}", "std": f"{round(np.std(sync_vals)/unit, 2)}{unit_str}", "min": f"{round(np.min(sync_vals)/unit, 2)}{unit_str}", "max": f"{round(np.max(sync_vals)/unit, 2)}{unit_str}"},
                    "async_no_router": {"mean": f"{round(np.mean(async_no_router_vals)/unit, 2)}{unit_str}", "std": f"{round(np.std(async_no_router_vals)/unit, 2)}{unit_str}", "min": f"{round(np.min(async_no_router_vals)/unit, 2)}{unit_str}", "max": f"{round(np.max(async_no_router_vals)/unit, 2)}{unit_str}"},
                    "async_with_router": {"mean": f"{round(np.mean(async_with_router_vals)/unit, 2)}{unit_str}", "std": f"{round(np.std(async_with_router_vals)/unit, 2)}{unit_str}", "min": f"{round(np.min(async_with_router_vals)/unit, 2)}{unit_str}", "max": f"{round(np.max(async_with_router_vals)/unit, 2)}{unit_str}"},
                    "gains_energy": {"mean": f"{round(np.mean(gains_energy), 2)}%", "std": f"{round(np.std(gains_energy), 2)}%", "min": f"{round(np.min(gains_energy), 2)}%", "max": f"{round(np.max(gains_energy), 2)}%"},
                    "gains_time": {"mean": f"{round(np.mean(gains_time), 2)}%", "std": f"{round(np.std(gains_time), 2)}%", "min": f"{round(np.min(gains_time), 2)}%", "max": f"{round(np.max(gains_time), 2)}%"},
                    "time_sync": {"mean": f"{round(np.mean(time_sync_vals)/3600, 2)} hours", "std": f"{round(np.std(time_sync_vals)/3600, 2)} hours", "min": f"{round(np.min(time_sync_vals)/3600, 2)} hours", "max": f"{round(np.max(time_sync_vals)/3600, 2)} hours"},
                    "time_async": {"mean": f"{round(np.mean(time_async_vals)/3600, 2)} hours", "std": f"{round(np.std(time_async_vals)/3600, 2)} hours", "min": f"{round(np.min(time_async_vals)/3600, 2)} hours", "max": f"{round(np.max(time_async_vals)/3600, 2)} hours"},
                    "gains_sync_energy_60_ud": {"mean": f"{round(np.mean(gains_sync_energy_60_ud), 2)}%", "std": f"{round(np.std(gains_sync_energy_60_ud), 2)}%", "min": f"{round(np.min(gains_sync_energy_60_ud), 2)}%", "max": f"{round(np.max(gains_sync_energy_60_ud), 2)}%"},
                    "gains_sync_time_60_ud": {"mean": f"{round(np.mean(gains_sync_time_60_ud), 2)}%", "std": f"{round(np.std(gains_sync_time_60_ud), 2)}%", "min": f"{round(np.min(gains_sync_time_60_ud), 2)}%", "max": f"{round(np.max(gains_sync_time_60_ud), 2)}%"},
                    "gains_async_energy_60_ud": {"mean": f"{round(np.mean(gains_async_energy_60_ud), 2)}%", "std": f"{round(np.std(gains_async_energy_60_ud), 2)}%", "min": f"{round(np.min(gains_async_energy_60_ud), 2)}%", "max": f"{round(np.max(gains_async_energy_60_ud), 2)}%"},
                    "gains_async_time_60_ud": {"mean": f"{round(np.mean(gains_async_time_60_ud), 2)}%", "std": f"{round(np.std(gains_async_time_60_ud), 2)}%", "min": f"{round(np.min(gains_async_time_60_ud), 2)}%", "max": f"{round(np.max(gains_async_time_60_ud), 2)}%"},
                    "detail_ons_sync": {"idles": {}, "reconfs": {}, "sendings": {}, "receives": {}, "comms": {}},
                    "detail_ons_async": {"idles": {}, "reconfs": {}, "sendings": {}, "receives": {}, "comms": {}},
                    "detail_router": {"idles": {}, "reconfs": {}, "sendings": {}, "receives": {}, "comms": {}},
                }

                for type_conso in type_consos:
                    energy_gain_by_uptime_durations_mean_std[scenario][ud][nb_deps]["total_stats"]["detail_ons_sync"][type_conso] = {
                        "mean": round(np.mean(detail_ons_sync[type_conso])/unit, 2),
                        "std": round(np.std(detail_ons_sync[type_conso])/unit, 2),
                        "min": round(np.min(detail_ons_sync[type_conso])/unit, 2),
                        "max": round(np.max(detail_ons_sync[type_conso])/unit, 2)
                    }
                    energy_gain_by_uptime_durations_mean_std[scenario][ud][nb_deps]["total_stats"]["detail_ons_async"][type_conso] = {
                        "mean": round(np.mean(detail_ons_async[type_conso])/unit, 2),
                        "std": round(np.std(detail_ons_async[type_conso])/unit, 2),
                        "min": round(np.min(detail_ons_async[type_conso])/unit, 2),
                        "max": round(np.max(detail_ons_async[type_conso])/unit, 2)
                    }
                    energy_gain_by_uptime_durations_mean_std[scenario][ud][nb_deps]["total_stats"]["detail_router"][type_conso] = {
                        "mean": round(np.mean(detail_router[type_conso])/unit, 2),
                        "std": round(np.std(detail_router[type_conso])/unit, 2),
                        "min": round(np.min(detail_router[type_conso])/unit, 2),
                        "max": round(np.max(detail_router[type_conso])/unit, 2)
                    }

                energy_gain_by_uptime_durations_mean_std[scenario][ud][nb_deps]["total_stats"]["detail_ons_sync"]["comms"] = {
                    "mean": round(np.mean(detail_ons_sync["comms"]) / unit, 2),
                    "std": round(np.std(detail_ons_sync["comms"]) / unit, 2),
                    "min": round(np.min(detail_ons_sync["comms"]) / unit, 2),
                    "max": round(np.max(detail_ons_sync["comms"]) / unit, 2)
                }
                energy_gain_by_uptime_durations_mean_std[scenario][ud][nb_deps]["total_stats"]["detail_ons_async"]["comms"] = {
                    "mean": round(np.mean(detail_ons_async["comms"]) / unit, 2),
                    "std": round(np.std(detail_ons_async["comms"]) / unit, 2),
                    "min": round(np.min(detail_ons_async["comms"]) / unit, 2),
                    "max": round(np.max(detail_ons_async["comms"]) / unit, 2)
                }
                energy_gain_by_uptime_durations_mean_std[scenario][ud][nb_deps]["total_stats"]["detail_router"]["comms"] = {
                    "mean": round(np.mean(detail_router["comms"]) / unit, 2),
                    "std": round(np.std(detail_router["comms"]) / unit, 2),
                    "min": round(np.min(detail_router["comms"]) / unit, 2),
                    "max": round(np.max(detail_router["comms"]) / unit, 2)
                }

    return energy_gain_by_uptime_durations_mean_std


def compute_energy_gain_from_param(param, path_executions_runs, conso_name):
    print(f"Param {param}")
    with open(f"{path_executions_runs}/aggregated_{param}.json") as f:
        all_global_results = ujson.load(f)

    print("Results loaded")
    global_results_accumulated = accumulate_global_results(all_global_results)
    print("Results accumulated")

    energy_gains = compute_energy_gain(global_results_accumulated, conso_name)
    energy_gain_by_nb_deps = compute_energy_gain_by_nb_deps(energy_gains)
    energy_gain_by_uptime_durations = compute_energy_gain_by_uptime_durations(energy_gain_by_nb_deps)
    print("Energy gains computed")
    return energy_gain_by_uptime_durations


def compute_tot(type_tot):
    # params_list = ["0-1.339-pullc-lora", "1.358-1.339-pullc-lora", "0-1.339-pullc-nbiot", "1.358-1.339-pullc-nbiot"]
    # params_list = ["1.358-1.339-pullc-lora", "1.358-1.339-pullc-nbiot"]
    params_list = ["1.358-1.339-pullc-lora"]
    path_executions_runs = f"{os.environ['HOME']}/results-reconfiguration-esds/results-greencom/esds-executions-runs"
    print("Loading results")

    for param in params_list:
        for conso_name in ["static", "dynamic"]:
        # for conso_name in ["dynamic"]:
            energy_gain_by_uptime_durations = compute_energy_gain_from_param(param, path_executions_runs, conso_name)
            energy_gain_by_uptime_durations_mean_std = _compute_stats_energy_gains(energy_gain_by_uptime_durations, conso_name)
            print("Energy gain prepared")

            print("--- Tot ---")
            for scenario_name, ud_values in energy_gain_by_uptime_durations_mean_std.items():
                for ud, nb_deps_values in ud_values.items():
                    for nb_dep in nb_deps_values.keys():
                        if nb_dep >= 5:
                            stats = nb_deps_values[nb_dep]["total_stats"]
                            print(param, conso_name, scenario_name, ud, nb_dep)
                            if type_tot == "energy":
                                # print(f"direct: {stats['sync']}")
                                # print(f"with rn: {stats['async_with_router']}")
                                # print(f"gain: {stats['gains_energy']}")
                                print(f"energy gain direct compared to 60 uptime: {stats['gains_sync_energy_60_ud']}")
                                # print(f"energy gain rn compared to 60 uptime: {stats['gains_async_energy_60_ud']}")
                                # if uds.index(ud) > 0:
                                #     ud_60_stats = ud_values[uds[uds.index(ud)-1]][nb_dep]["total_stats"]
                                #     sync_gain_60_ud = round((ud_60_stats["sync"]-stats["sync"])*100/ud_60_stats["sync"],2)
                                #     async_gain_60_ud = round((ud_60_stats["async_with_router"]-stats["async_with_router"])*100/ud_60_stats["async_with_router"],2)
                                #     print(f"energy gain direct compared to 60 uptime: {sync_gain_60_ud}%")
                                #     print(f"energy gain direct compared to 60 uptime: {async_gain_60_ud}%")
                            else:
                                # print(f"direct: {stats['time_sync']}")
                                # print(f"with rn: {stats['time_async']}")
                                # print(f"gain: {stats['gains_time']}")
                                print(f"time gain direct compared to 60 uptime: {stats['gains_sync_time_60_ud']}")
                                # print(f"time gain rn compared to 60 uptime: {stats['gains_async_time_60_ud']}")
                                # if uds.index(ud) > 0:
                                #     ud_60_stats = ud_values[uds[uds.index(ud)-1]][nb_dep]["total_stats"]
                                #     sync_gain_60_ud = round((ud_60_stats["time_sync"]-stats["time_sync"])*100/ud_60_stats["time_sync"],2)
                                #     async_gain_60_ud = round((ud_60_stats["time_async"]-stats["time_async"])*100/ud_60_stats["time_async"],2)
                                #     print(f"time gain direct compared to 60 uptime: {sync_gain_60_ud}%")
                                #     print(f"time gain direct compared to 60 uptime: {async_gain_60_ud}%")
                            # print()


def compute_comms():
    # params_list = ["1.358-1.339-pullc-lora", "1.358-1.339-pullc-nbiot"]
    path_executions_runs = f"{os.environ['HOME']}/results-reconfiguration-esds/results-greencom/esds-executions-runs"
    conso_name = "dynamic"
    energy_gain_by_uptime_durations_lora = compute_energy_gain_from_param("1.358-1.339-pullc-lora", path_executions_runs, conso_name)
    energy_gain_by_uptime_durations_nbiot = compute_energy_gain_from_param("1.358-1.339-pullc-nbiot", path_executions_runs, conso_name)
    results_comms_stats = {}
    for scenario in energy_gain_by_uptime_durations_lora.keys():
        for ud in energy_gain_by_uptime_durations_lora[scenario].keys():
            for nb_dep in energy_gain_by_uptime_durations_lora[scenario][ud].keys():
                if nb_dep < 5: continue
                lora_runs_list = []
                nbiot_runs_list = []
                gains_runs_list = []
                for num_run in energy_gain_by_uptime_durations_lora[scenario][ud][nb_dep].keys():
                    total_lora = energy_gain_by_uptime_durations_lora[scenario][ud][nb_dep][num_run]["total"]
                    total_nbiot = energy_gain_by_uptime_durations_nbiot[scenario][ud][nb_dep][num_run]["total"]
                    # results_comms_run.setdefault(scenario,{}).setdefault(ud,{}).setdefault(nb_dep,{}).setdefault("lora",[]).append(total_lora["detail_ons_sync"]["sendings"] + total_lora["detail_ons_sync"]["receives"])
                    # results_comms_run[scenario][ud][nb_dep].setdefault("nbiot",[]).append(total_nbiot["detail_ons_sync"]["sendings"] + total_nbiot["detail_ons_sync"]["receives"])
                    total_lora_comms = total_lora["detail_ons_sync"]["sendings"] + total_lora["detail_ons_sync"]["receives"]
                    total_nbiot_comms = total_nbiot["detail_ons_sync"]["sendings"] + total_nbiot["detail_ons_sync"]["receives"]
                    lora_runs_list.append(total_lora_comms)
                    nbiot_runs_list.append(total_nbiot_comms)
                    gains_runs_list.append((total_nbiot_comms-total_lora_comms)*100/total_lora_comms)

                lora_stats = {
                    "mean": f"{round(np.mean(lora_runs_list), 2)}J",
                    "std": f"{round(np.std(lora_runs_list), 2)}J",
                    "min": f"{round(np.min(lora_runs_list), 2)}J",
                    "max": f"{round(np.max(lora_runs_list), 2)}J",
                }
                nbiot_stats = {
                    "mean": f"{round(np.mean(nbiot_runs_list), 2)}J",
                    "std": f"{round(np.std(nbiot_runs_list), 2)}J",
                    "min": f"{round(np.min(nbiot_runs_list), 2)}J",
                    "max": f"{round(np.max(nbiot_runs_list), 2)}J",
                }
                gains_stats = {
                    "mean": f"{round(np.mean(gains_runs_list), 2)}%",
                    "std": f"{round(np.std(gains_runs_list), 2)}%",
                    "min": f"{round(np.min(gains_runs_list), 2)}%",
                    "max": f"{round(np.max(gains_runs_list), 2)}%",
                }

                results_comms_stats.setdefault(scenario, {}).setdefault(ud, {}).setdefault(nb_dep, {})["lora"] = lora_stats
                results_comms_stats.setdefault(scenario, {}).setdefault(ud, {}).setdefault(nb_dep, {})["nbiot"] = nbiot_stats
                results_comms_stats.setdefault(scenario, {}).setdefault(ud, {}).setdefault(nb_dep, {})["gains"] = gains_stats

                print(scenario, ud, nb_dep)
                print("lora", lora_stats)
                print("nbiot", nbiot_stats)
                print("gains", gains_stats)



    # energy_gain_by_uptime_durations_mean_std = _compute_stats_energy_gains(energy_gain_by_uptime_durations, conso_name)


if __name__ == "__main__":
    # compute_comms()
    compute_tot("energy")
    # print("--- Comms ---")
    # techno_name = param.split("-")[-1]
    # for scenario_name, ud_values in energy_gain_by_uptime_durations_mean_std.items():
    #     for ud, nb_deps_values in ud_values.items():
    #         for nb_dep in nb_deps_values.keys():
    #             if nb_dep >= 5:
    #                 stats = nb_deps_values[nb_dep]["total_stats"]
    #                 results_comms.setdefault(scenario_name, {}).setdefault(ud, {}).setdefault(nb_dep, {})[techno_name] = stats['detail_ons_sync']['comms']
                    # print(scenario_name, ud, nb_dep)
                    # print(f"conso: {stats['detail_ons_sync']['comms']}")
                    # print()
    # plot_bar_results(energy_gain_by_uptime_durations_mean_std, param)
    # plot_scatter_results(energy_gain_by_nb_deps, param)
    # plot_surface_results(None, None)
    # for s, ud_vals in results_comms.items():
    #     for ud, nb_deps_vals in ud_vals.items():
    #         for nb_dep, comms_vals in nb_deps_vals.items():
    #             lora = comms_vals["lora"]
    #             nbiot = comms_vals["nbiot"]
    #             gain = comms_vals["gain"]
    # print(json.dumps(results_comms, indent=4))
