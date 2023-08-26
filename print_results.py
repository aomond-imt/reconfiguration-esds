import collections
import itertools
import os

import yaml
import numpy as np
import matplotlib.pyplot as plt


def _gather_results(global_results):
    gathered_results = {}
    for key, nodes_results in global_results.items():
        router_id = max(nodes_results["energy"]["idles"].keys())
        energy_results = nodes_results["energy"]
        gathered_results[key] = {"energy": {}, "time": nodes_results["time"]}
        # print(f"{key}:")
        # print(f"idles: {nodes_results['idles']}")
        # print(f"reconfs: {nodes_results['reconfs']}")
        # print(f"sendings: {nodes_results['sendings']}")
        # print(f"receives: {nodes_results['receives']}")
        filter_tot = ["reconfs", "sendings", "receives"]
        for node_id in sorted(energy_results["idles"].keys()):
            tot = 0
            s = {"idles": 0, "reconfs": 0, "sendings": 0, "receives": 0}
            for name in s.keys():
                s[name] += energy_results[name][node_id]["node_conso"] + energy_results[name][node_id]["comms_cons"]
                if name in filter_tot or node_id == router_id:
                    tot += s[name]
            s.update({
                "tot_msg_sent": energy_results["sendings"][node_id]["tot_msg_sent"],
                "tot_ack_received": energy_results["sendings"][node_id]["tot_ack_received"],
                "tot_wait_polling": energy_results["sendings"][node_id]["tot_wait_polling"],
                "tot_msg_received": energy_results["receives"][node_id]["tot_msg_received"],
                "tot_msg_responded": energy_results["receives"][node_id]["tot_msg_responded"]
            })

            gathered_results[key]["energy"][node_id] = {"tot": round(tot, 2), "detail": s}
            # print(f"{node_id}: {round(tot, 2)}J --- Detail: {s}")
    return gathered_results


def print_energy_results(global_results):
    print(" ------------ Results --------------")
    gathered_results = _gather_results(global_results)

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


def analyse_energy_results(global_results):
    print(" ------------ Results --------------")
    gathered_results = _gather_results(global_results)
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


def compute_energy_gain(global_results):
    gathered_results = _gather_results(global_results)
    group_by_version_concerto_d = _group_by_version_concerto_d(gathered_results)
    all_results = {}
    for key, vals in group_by_version_concerto_d.items():
        if "async" not in vals.keys() or "sync" not in vals.keys():
            print(f"{key}: Async or sync missing, skip")
            continue
        router_id = max(vals["async"]["energy"].keys())
        assert router_id == max(vals["sync"]["energy"].keys())
        all_results[key] = {}
        tot_ons_sync = 0
        tot_ons_async = 0
        tot_router = 0
        tot_detail = {}
        for name in ["detail_ons_sync", "detail_ons_async", "detail_router"]:
            tot_detail[name] = {"idles": 0, "reconfs": 0, "sendings": 0, "receives": 0}

        for vals_sync, vals_async in zip(vals["sync"]["energy"].items(), vals["async"]["energy"].items()):
            node_id, node_results_sync = vals_sync
            _, node_results_async = vals_async
            tot_gain = node_results_async["tot"] - node_results_sync["tot"]
            if node_id == router_id:
                tot_router = node_results_async["tot"]
            else:
                tot_ons_sync += node_results_sync["tot"]
                tot_ons_async += node_results_async["tot"]
            all_results[key][node_id] = {"gain": round(tot_gain, 2), "sync": node_results_sync['tot'], "async": node_results_async['tot']}
            all_results[key][node_id]["details"] = {}
            for detail_sync, detail_async in zip(node_results_sync["detail"].items(), node_results_async["detail"].items()):
                name, val_sync = detail_sync
                name_a, val_async = detail_async
                assert name == name_a
                if name not in ["idles", "reconfs", "sendings", "receives"]:
                    continue
                gain = val_async - val_sync
                all_results[key][node_id]["details"][name] = {"gain": round(gain, 2), "sync": val_sync, "async": val_async}

                if node_id < router_id:
                    tot_detail["detail_ons_sync"][name] += val_sync
                    tot_detail["detail_ons_async"][name] += val_async
                else:
                    tot_detail["detail_router"][name] += val_async

        all_results[key]["total"] = {
            "sync": round(tot_ons_sync, 2),
            "async_no_router": round(tot_ons_async, 2),
            "async_with_router": round(tot_ons_async + tot_router, 2),
            "gain_no_router": round((tot_ons_sync - tot_ons_async) * 100 / tot_ons_sync, 2),
            "gain_with_router": round((tot_ons_sync - (tot_ons_async+tot_router)) * 100 / tot_ons_sync, 2),
            "time_sync": vals["sync"]["time"],
            "time_async": vals["async"]["time"],
            "gain_time": round((vals["sync"]["time"] - vals["async"]["time"]) * 100 / vals["sync"]["time"], 2)
        }
        all_results[key]["total"].update(tot_detail)

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
        scenario = "-".join(key.split("-")[:-2])
        if scenario not in energy_gain_by_nb_deps.keys():
            energy_gain_by_nb_deps[scenario] = {}
        nb_deps = int(key.split("-")[7:-1][0])
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


def plot_bar_results(energy_gain_by_nb_deps, param_names):
    for scenario_name, gain_by_nb_deps in energy_gain_by_nb_deps.items():
        # scenario_name = 'esds_generated_data-ud0_od0_30_25-deploy-T0'
        # gain_by_nb_deps = energy_gain_by_nb_deps[scenario_name]
        x = np.arange(len(gain_by_nb_deps.keys()))
        elements = {
            "sync": {
                "ons": [el["total"]["sync"] for el in gain_by_nb_deps.values()],
                "detail_ons_idles": [el["total"]["detail_ons_sync"]["idles"] for el in gain_by_nb_deps.values()],
                "detail_ons_reconfs": [el["total"]["detail_ons_sync"]["reconfs"] for el in gain_by_nb_deps.values()],
                "detail_ons_sendings": [el["total"]["detail_ons_sync"]["sendings"] for el in gain_by_nb_deps.values()],
                "detail_ons_receives": [el["total"]["detail_ons_sync"]["receives"] for el in gain_by_nb_deps.values()],
                "time_sync": [el["total"]["time_sync"] for el in gain_by_nb_deps.values()],
            },
            "async": {
                "ons": [el["total"]["async_no_router"] for el in gain_by_nb_deps.values()],
                "detail_ons_idles": [el["total"]["detail_ons_async"]["idles"] for el in gain_by_nb_deps.values()],
                "detail_ons_reconfs": [el["total"]["detail_ons_async"]["reconfs"] for el in gain_by_nb_deps.values()],
                "detail_ons_sendings": [el["total"]["detail_ons_async"]["sendings"] for el in gain_by_nb_deps.values()],
                "detail_ons_receives": [el["total"]["detail_ons_async"]["receives"] for el in gain_by_nb_deps.values()],
                "router": [el["total"]["async_with_router"]-el["total"]["async_no_router"] for el in gain_by_nb_deps.values()],
                "detail_router_idles": [el["total"]["detail_router"]["idles"] for el in gain_by_nb_deps.values()],
                "detail_router_reconfs": [el["total"]["detail_router"]["reconfs"] for el in gain_by_nb_deps.values()],
                "detail_router_sendings": [el["total"]["detail_router"]["sendings"] for el in gain_by_nb_deps.values()],
                "detail_router_receives": [el["total"]["detail_router"]["receives"] for el in gain_by_nb_deps.values()],
                "time_async": [el["total"]["time_async"] for el in gain_by_nb_deps.values()],
            },
        }
        # print(json.dumps(elements, indent=2))

        bottom = {
            "sync": np.zeros(len(gain_by_nb_deps.keys())),
            "async": np.zeros(len(gain_by_nb_deps.keys())),
        }
        # fig, ax = plt.subplots()
        fig, ax = plt.subplots(figsize=(10, 10))
        multiplier = 0
        width = 0.4
        max_bound = 0
        for attribute, measurement in elements.items():
            offset = width * multiplier
            # max_bound = _plot_tot(attribute, ax, bottom, max_bound, measurement, offset, width, x)
            max_bound = _plot_detail(attribute, ax, bottom, max_bound, measurement, offset, width, x)
            # max_bound = _plot_tot_time(attribute, ax, bottom, max_bound, measurement, offset, width, x)
            multiplier += 1

        ax.set_ylabel('Energy (J)')
        ax.set_xlabel('Nb deps')
        title = f'{scenario_name}-{param_names}'
        ax.set_title(title)
        ax.set_xticks(x + width, gain_by_nb_deps.keys())
        ax.legend(loc='upper left', ncols=3)
        # ax.set_ylim(0, max_bound + 100)
        ax.set_ylim(0, max_bound * 1.1)

        plt.show()
        # dir_to_save = f"/home/aomond/reconfiguration-esds/concerto-d-results/pycharm_plots/detail_update/{param_names}"
        # # dir_to_save = f"/home/aomond/reconfiguration-esds/concerto-d-results/pycharm_plots/detail/{param_names}"
        # os.makedirs(dir_to_save, exist_ok=True)
        # plt.savefig(f"{dir_to_save}/{scenario_name}.png")


def _plot_tot(attribute, ax, bottom, max_bound, measurement, offset, width, x):
    if attribute == "sync":
        rects = ax.bar(x + offset, measurement["ons"], width, bottom=bottom[attribute], label=attribute)
        bottom[attribute] = bottom[attribute] + measurement["ons"]
        ax.bar_label(rects, padding=3)
        max_bound = max(max_bound, max(bottom[attribute]))
    elif attribute == "async":
        rects = ax.bar(x + offset, measurement["ons"], width, bottom=bottom[attribute], label="async (ons)")
        bottom[attribute] = bottom[attribute] + measurement["ons"]
        # ax.bar_label(rects, padding=3)
        rects = ax.bar(x + offset, measurement["router"], width, bottom=bottom[attribute], label="async (router)")
        bottom[attribute] = bottom[attribute] + measurement["router"]
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


def _plot_detail(attribute, ax, bottom, max_bound, measurement, offset, width, x):
    if attribute == "sync":
        # rects = ax.bar(x + offset, measurement["detail_ons_idles"], width, bottom=bottom[attribute], label="sync ons (idles)")
        # bottom[attribute] = bottom[attribute] + measurement["detail_ons_idles"]
        rects = ax.bar(x + offset, measurement["detail_ons_reconfs"], width, bottom=bottom[attribute], label="sync ons (reconfs)")
        bottom[attribute] = bottom[attribute] + measurement["detail_ons_reconfs"]
        ax.bar_label(rects, padding=3)
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
        rects = ax.bar(x + offset, measurement["detail_ons_reconfs"], width, bottom=bottom[attribute], label="async ons (reconfs)")
        bottom[attribute] = bottom[attribute] + measurement["detail_ons_reconfs"]
        ax.bar_label(rects, padding=3)
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


if __name__ == "__main__":
    # name_params = ["1.2-1.38-nbiot-pullc", "1.2-1.38-lora-pullc", "0-1.38-nbiot-pullc"]
    # name_params = ["1.2-1.38-lora-pullc"]

    # for param in name_params:
    # results_dir = "/home/aomond/reconfiguration-esds/concerto-d-results/global_results-0-1.38-lora-pullc.yaml"
    # results_dir = "/home/aomond/reconfiguration-esds/concerto-d-results/global_results-0-1.38-nbiot-pullc.yaml"
    # results_dir = "/home/aomond/reconfiguration-esds/concerto-d-results/global_results-1.2-1.38-lora-pullc.yaml"
    # results_dir = f"/home/aomond/reconfiguration-esds/concerto-d-results/to_analyse_test/"
    results_dir = "/home/aomond/reconfiguration-esds/to_analyse/"
    # param = "0-1.339-lora-pullc"
    # param = "1.237-1.339-lora-pullc"
    # param = "1.358-1.339-lora-pullc"
    # param = "0.181-1.5778-lora-pullc"
    params_list = ["0-1.339-lora-pullc"]
    # params_list = ["0-1.339-lora-pullc", "1.237-1.339-lora-pullc", "1.358-1.339-lora-pullc"]
    # params_list = ["0-1.339-lora-pullc", "0-1.339-nbiot-pullc", "1.237-1.339-lora-pullc", "1.237-1.339-nbiot-pullc"]
    for param in params_list:
        global_results = {}
        for file in os.listdir(results_dir):
            if param in file and "T1" in file and "deploy" in file:
                with open(os.path.join(results_dir,file)) as f:
                    global_results.update(yaml.safe_load(f))

        # results_dir = "/home/aomond/reconfiguration-esds/saved_results/global_results-1.2-1.38-lora-pullc-7-overlaps.yaml"
        # results_dir = f"/home/aomond/reconfiguration-esds/saved_results/global_results-{param}-7-overlaps.yaml"

        # print_energy_results(global_results)
        # analyse_energy_results(global_results)
        energy_gains = compute_energy_gain(global_results)
        energy_gain_by_nb_deps = compute_energy_gain_by_nb_deps(energy_gains)
        # print(json.dumps(energy_gains, indent=4))
        # print_energy_gain(energy_gains)
        plot_bar_results(energy_gain_by_nb_deps, param)
        # plot_scatter_results(energy_gain_by_nb_deps, param)
        # plot_surface_results(None, None)
