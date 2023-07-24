import yaml


def print_results():
    results_dir = "/tmp/global_results.yaml"
    with open(results_dir) as f:
        global_results = yaml.safe_load(f)

    print(" ------------ Results --------------")
    for key, nodes_results in global_results.items():
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
            print(f"{node_id}: {round(tot, 2)}J --- Detail: {s}")
    print("------------------------------------")


if __name__ == "__main__":
    print_results()
