import os

import ujson
import yaml

if __name__ == "__main__":
    params_list = ["0-1.339-pullc-lora", "1.358-1.339-pullc-lora", "0-1.339-pullc-nbiot", "1.358-1.339-pullc-nbiot"]
    # params_list = ["1.358-1.339-lora-pullc", "0-1.339-nbiot-pullc", "1.358-1.339-nbiot-pullc"]
    path_executions_runs = f"{os.environ['HOME']}/results-reconfiguration-esds/results-greencom/esds-executions-runs"
    print("Loading results")
    for param in params_list:
        all_global_results = {}
        print(f"Param {param}")
        for num_run in range(200):
            print(f"Run {num_run}")
            results_dir = f"{path_executions_runs}/{num_run}"
            global_results = {}
            for file in os.listdir(results_dir):
                if param in file:
                    with open(os.path.join(results_dir, file)) as f:
                        global_results.update(yaml.safe_load(f))

            all_global_results[num_run] = global_results

        with open(f"{path_executions_runs}/aggregated_{param}.json", "w") as f:
            ujson.dump(all_global_results, f)
