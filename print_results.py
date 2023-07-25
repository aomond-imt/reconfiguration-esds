import yaml

results_dir = "/home/aomond/reconfiguration-esds/concerto-d-results/saved_results/results_6_expes_big_power/global_results.yaml"


def _gather_results(global_results):
    gathered_results = {}
    for key, nodes_results in global_results.items():
        gathered_results[key] = {}
        # print(f"{key}:")
        # print(f"idles: {nodes_results['idles']}")
        # print(f"reconfs: {nodes_results['reconfs']}")
        # print(f"sendings: {nodes_results['sendings']}")
        # print(f"receives: {nodes_results['receives']}")
        filter_tot = ["reconfs", "sendings", "receives"]
        for node_id in sorted(nodes_results["idles"].keys()):
            tot = 0
            s = {"idles": 0, "reconfs": 0, "sendings": 0, "receives": 0}
            for name in s.keys():
                s[name] += nodes_results[name][node_id]["node_conso"] + nodes_results[name][node_id]["comms_cons"]
                if name in filter_tot:
                    tot += s[name]

            gathered_results[key][node_id] = {"tot": round(tot, 2), "detail": s}
            # print(f"{node_id}: {round(tot, 2)}J --- Detail: {s}")
    return gathered_results


def print_results():
    with open(results_dir) as f:
        global_results = yaml.safe_load(f)

    print(" ------------ Results --------------")
    gathered_results = _gather_results(global_results)

    for key, vals in gathered_results.items():
        print(key)
        for node_id, res in vals.items():
            print(f"{node_id}: {round(res['tot'], 2)}J --- Detail: {res['detail']}")
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


def analyse_results():
    with open(results_dir) as f:
        global_results = yaml.safe_load(f)

    print(" ------------ Results --------------")
    gathered_results = _gather_results(global_results)
    group_by_version_concerto_d = _group_by_version_concerto_d(gathered_results)
    for key, vals in group_by_version_concerto_d.items():
        print(key)
        if "sync" in vals.keys():
            print("sync")
            for node_id, res in vals["sync"].items():
                print(f"{node_id}: {round(res['tot'], 2)}J --- Detail: {res['detail']}")
        if "async" in vals.keys():
            print("async")
            for node_id, res in vals["async"].items():
                print(f"{node_id}: {round(res['tot'], 2)}J --- Detail: {res['detail']}")


def compute_gain():
    with open(results_dir) as f:
        global_results = yaml.safe_load(f)
    gathered_results = _gather_results(global_results)
    group_by_version_concerto_d = _group_by_version_concerto_d(gathered_results)
    for key, vals in group_by_version_concerto_d.items():
        print(key)
        for vals_sync, vals_async in zip(vals["sync"].items(), vals["async"].items()):
            node_id, node_results_sync = vals_sync
            _, node_results_async = vals_async
            tot_gain = node_results_sync["tot"] - node_results_async["tot"]
            sign = "-" if tot_gain > 0 else "+"
            print(f"{node_id}: tot_gain: {sign}{abs(round(tot_gain, 2))}J", end=" - ")

            for detail_sync, detail_async in zip(node_results_sync["detail"].items(), node_results_async["detail"].items()):
                name, val_sync = detail_sync
                _, val_async = detail_async
                gain = val_sync - val_async
                s = "-" if gain > 0 else "+"
                print(f"{name}: {s}{abs(round(gain, 2))}J", end=", ")
            print()



if __name__ == "__main__":
    # print_results()
    # analyse_results()
    compute_gain()
