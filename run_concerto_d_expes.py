#!/usr/bin/env python
import collections
import math
import os,subprocess,time
import shutil
import traceback
from multiprocessing import Pool, cpu_count
from pathlib import Path

import yaml
from execo_engine import ParamSweeper

import print_results
import simulation_functions

OFF_POWER = 0
ON_POWER = 0.4
LORA_POWER = 0.16

limit_expes = math.inf
tests_timeout=20000 # Max duration of a test


def _assert_value(node_id, key, val, expected_val):
    try:
        assert abs(val - expected_val) <= 0.01
    except AssertionError as e:
        print(f"Assertion error: node_id: {node_id} - key: {key} - val: {val} - expected: {expected_val}")
        raise e


def _esds_results_verification(esds_parameters, expe_esds_verification_files, idle_results_dir, reconf_results_dir, sends_results_dir, receive_results_dir, execution_dir, stressConso, idleConso):
    # Retrieve verification file for the given configuration file
    # verification = None
    # for verif_file in os.listdir(expe_esds_verification_files):
    #     if Path(verif_file).stem == title:
    #         abs_verif_file = os.path.join(expe_esds_verification_files, verif_file)
    #         with open(abs_verif_file) as f:
    #             verification = yaml.safe_load(f)

    # Retrieve results files for reconfs, sends and receives
    idle_results = os.path.join(idle_results_dir, execution_dir)
    reconfs_results = os.path.join(reconf_results_dir, execution_dir)
    sends_results = os.path.join(sends_results_dir, execution_dir)
    receive_results = os.path.join(receive_results_dir, execution_dir)

    list_files_idles = sorted(os.listdir(idle_results), key=lambda f_name: int(Path(f_name).stem))
    list_files_reconfs = sorted(os.listdir(reconfs_results), key=lambda f_name: int(Path(f_name).stem))
    list_files_sends = sorted(os.listdir(sends_results), key=lambda f_name: int(Path(f_name).stem))
    list_files_receives = sorted(os.listdir(receive_results), key=lambda f_name: int(Path(f_name).stem))

    for node_idle_file, node_reconf_file, node_send_file, node_receive_file in zip(list_files_idles, list_files_reconfs, list_files_sends, list_files_receives):
        with open(os.path.join(idle_results, node_idle_file)) as f:
            results_idle = yaml.safe_load(f)
        with open(os.path.join(reconfs_results, node_reconf_file)) as f:
            results_reconf = yaml.safe_load(f)
        with open(os.path.join(sends_results, node_send_file)) as f:
            results_send = yaml.safe_load(f)
        with open(os.path.join(receive_results, node_receive_file)) as f:
            results_receive = yaml.safe_load(f)

        assert int(Path(node_idle_file).stem) == int(Path(node_reconf_file).stem) == int(Path(node_send_file).stem) == int(Path(node_receive_file).stem)
        node_id = int(Path(node_idle_file).stem)
        max_exec_duration = esds_parameters["max_execution_duration"]

        # Verification idles
        node_uptimes = esds_parameters["uptimes_periods_per_node"][node_id]
        expected_uptime = sum(end-start for start, end in node_uptimes)
        expected_no_uptime = max_exec_duration - expected_uptime
        _assert_value(node_id, "tot_uptime", results_idle["tot_uptime"], expected_uptime)
        _assert_value(node_id, "tot_sleeping_time", results_idle["tot_sleeping_time"], expected_no_uptime)
        if results_idle["is_router"]:
            expected_idle_conso = expected_uptime*(idleConso+stressConso)
        else:
            expected_idle_conso = expected_uptime*idleConso
        _assert_value(node_id, "node_conso", results_idle["node_conso"], expected_idle_conso)

        # Verification reconfs
        node_reconfs = esds_parameters["reconf_periods_per_node"][node_id]
        expected_reconf = sum((end-start) for start, end, nb_processes in node_reconfs if nb_processes > 0)
        expected_reconf_flat = sum(end-start for start, end, nb_processes in node_reconfs if nb_processes > 0)
        expected_no_reconf_time = max_exec_duration - expected_reconf_flat
        # nb_deps = len(list_files_idles) - 2
        # cpu_utilization_per_process = 1/nb_deps
        # expected_node_conso = sum((end-start)*nb_processes*cpu_utilization_per_process*stressConso for start, end, nb_processes in node_reconfs)
        expected_node_conso = sum((end-start)*stressConso for start, end, nb_processes in node_reconfs if nb_processes > 0)
        _assert_value(node_id, "tot_reconf_time", results_reconf["tot_reconf_time"], expected_reconf)
        _assert_value(node_id, "tot_reconf_flat_time", results_reconf["tot_reconf_flat_time"], expected_reconf_flat)
        _assert_value(node_id, "tot_no_reconf_time", results_reconf["tot_no_reconf_time"], expected_no_reconf_time)
        _assert_value(node_id, "node_conso", results_reconf["node_conso"], expected_node_conso)

        # Verification sending
        node_sendings = esds_parameters["sending_periods_per_node"][node_id]
        expected_sending_flat_time = sum(end - start for start, end, node_send in node_sendings if node_send != {})
        expected_no_sending_time = max_exec_duration - expected_sending_flat_time - expected_no_uptime
        _assert_value(node_id, "tot_sending_flat_time", results_send["tot_sending_flat_time"], expected_sending_flat_time)
        _assert_value(node_id, "tot_no_sending_time", results_send["tot_no_sending_time"], expected_no_sending_time)

        # Verification receive
        # node_receives = esds_parameters["receive_periods_per_node"][node_id]
        # expected_receive_flat_time = sum(end - start for start, end, node_send in node_receives if node_send != {})
        # expected_no_receive_time = max_exec_duration - expected_receive_flat_time - expected_no_uptime
        # _assert_value(node_id, "tot_receive_flat_time", results_receive["tot_receive_flat_time"], expected_receive_flat_time)
        # _assert_value(node_id, "tot_no_receive_time", results_receive["tot_no_receive_time"], expected_no_receive_time)


def _load_energetic_expe_results_from_title(execution_dir, idle_results_dir, reconf_results_dir, sends_results_dir, receive_results_dir):
    # Retrieve results files for reconfs, sends and receives
    idle_results = os.path.join(idle_results_dir, execution_dir)
    reconfs_results = os.path.join(reconf_results_dir, execution_dir)
    sends_results = os.path.join(sends_results_dir, execution_dir)
    receive_results = os.path.join(receive_results_dir, execution_dir)

    list_files_idles = sorted(os.listdir(idle_results), key=lambda f_name: int(Path(f_name).stem))
    list_files_reconfs = sorted(os.listdir(reconfs_results), key=lambda f_name: int(Path(f_name).stem))
    list_files_sends = sorted(os.listdir(sends_results), key=lambda f_name: int(Path(f_name).stem))
    list_files_receives = sorted(os.listdir(receive_results), key=lambda f_name: int(Path(f_name).stem))

    energetic_results_expe = {"idles": {}, "reconfs": {}, "sendings": {}, "receives": {}}
    for node_idle_file, node_reconf_file, node_send_file, node_receive_file in zip(list_files_idles, list_files_reconfs, list_files_sends, list_files_receives):
        with open(os.path.join(idle_results, node_idle_file)) as f:
            results_idle = yaml.safe_load(f)
        with open(os.path.join(reconfs_results, node_reconf_file)) as f:
            results_reconf = yaml.safe_load(f)
        with open(os.path.join(sends_results, node_send_file)) as f:
            results_send = yaml.safe_load(f)
        with open(os.path.join(receive_results, node_receive_file)) as f:
            results_receive = yaml.safe_load(f)
        node_id = int(Path(node_idle_file).stem)
        energetic_results_expe["idles"][node_id] = {"node_conso": results_idle["node_conso"], "comms_cons": results_idle["comms_cons"]}
        energetic_results_expe["reconfs"][node_id] = {"node_conso": results_reconf["node_conso"], "comms_cons": results_reconf["comms_cons"]}
        energetic_results_expe["sendings"][node_id] = {"node_conso": results_send["node_conso"], "comms_cons": results_send["comms_cons"], "tot_msg_sent": results_send["tot_msg_sent"], "tot_ack_received": results_send["tot_ack_received"], "tot_wait_polling": results_send["tot_wait_polling"]}
        energetic_results_expe["receives"][node_id] = {"node_conso": results_receive["node_conso"], "comms_cons": results_receive["comms_cons"], "tot_msg_received": results_receive["tot_msg_received"], "tot_msg_responded": results_receive["tot_msg_responded"]}

    return energetic_results_expe


def _group_by_version_concerto_d(parameter_files_list):
    parameter_files_dict = {}
    for key in parameter_files_list:
        version = "async" if "async" in key else "sync"
        key_without_version = "-".join(key.split(f"-{version}-"))
        if key_without_version not in parameter_files_dict.keys():
            parameter_files_dict[key_without_version] = {version: key}
        else:
            parameter_files_dict[key_without_version][version] = key
    ordered_parameter = collections.OrderedDict(sorted(parameter_files_dict.items()))
    ordered_parameter_list = []
    for _, vals in ordered_parameter.items():
        ordered_parameter_list.append(vals["sync"])
        ordered_parameter_list.append(vals["async"])
    return ordered_parameter_list


def main(simu_to_launch_dir="expe_esds_parameter_files_dao"):
    parallel_execs = []
    nb_cores = math.ceil(cpu_count() * 0.9)
    pool = Pool(nb_cores)
    for _ in range(nb_cores):
        exec_esds = pool.apply_async(
            _execute_esds_simulation,
            args=(simu_to_launch_dir,)
        )
        parallel_execs.append(exec_esds)

    for running_exec in parallel_execs:
        try:
            running_exec.get()
        except subprocess.TimeoutExpired as err:
            print("failed :(")
            print("------------- Test duration expired (timeout=" + str(tests_timeout) + "s) -------------")
            print(err.output, end="")
            # exit(1)
        except subprocess.CalledProcessError as err:
            print("failed :(")
            print("------------- Test has a non-zero exit code -------------")
            print(err.output, end="")
            # exit(2)
        except Exception as err:
            print("failed :(")
            traceback.print_exc()
            # exit(3)

        # print("Dump results")
        # global_results_path = f"global_results-{joined_params}.yaml"
        # with open(os.path.join(root, global_results_path), "w") as f:
        #     yaml.safe_dump(global_results, f)
        # print("Results dumped")
        # print(f"All passed in {sum_expes_duration:.2f}s")
        # global_results = {}
        # for file in os.listdir(f"{os.environ['HOME']}/reconfiguration-esds/concerto-d-results/to_analyse_test/"):
        #     with open(os.path.join(f"{os.environ['HOME']}/reconfiguration-esds/concerto-d-results/to_analyse_test/", file)) as f:
        #         global_results.update(yaml.safe_load(f))
        # print_results.print_energy_results(global_results)


def _execute_esds_simulation(simu_to_launch_dir):
    for num_run in range(100):
        # Setup variables
        ## Configuration files dirs
        root = f"{os.environ['HOME']}/reconfiguration-esds/concerto-d-results/{num_run}"
        os.makedirs(root, exist_ok=True)
        # expe_esds_parameter_files = os.path.join(root, "tests")
        expe_esds_parameter_files = os.path.join(root, simu_to_launch_dir)
        esds_current_parameter_file = os.path.join(root, "current_esds_parameter_file.yaml")
        expe_esds_verification_files = os.path.join(root, "expe_esds_verification_files")

        ## Results dirs
        results_dir = os.path.join(root, "results")
        idle_results_dir = os.path.join(results_dir, "idles")
        reconf_results_dir = os.path.join(results_dir, "reconfs")
        sends_results_dir = os.path.join(results_dir, "sends")
        receive_results_dir = os.path.join(results_dir, "receives")

        # Start experiments
        ## Clean previous results dirs
        # shutil.rmtree(results_dir, ignore_errors=True)

        ## Run all experiments
        # limit_expes = math.inf
        parameter_files_names = [f for f in os.listdir(expe_esds_parameter_files) if f.startswith("esds_generated_data")]
        parameter_files_list = _group_by_version_concerto_d(parameter_files_names)
        sum_expes_duration = 0
        nb_expes_tot = min(len(parameter_files_names), limit_expes)

        os.makedirs(os.path.join(root, "logs"), exist_ok=True)

        ## Getting sweeped parameters
        all_params = simulation_functions.get_simulation_swepped_parameters()
        nb_params_tot = len(all_params)
        sweeps = []
        for parameter in all_params:
            for parameter_file in parameter_files_list:
                if "sync-update-T1-30-pull" not in parameter_file:
                    parameter_tuple = (
                        parameter["stressConso"],
                        parameter["idleConso"],
                        parameter["typeSynchro"]
                    )
                    sweeps.append((parameter_tuple, parameter_file))

        sweeper = ParamSweeper(
            persistence_dir=os.path.join(root, "sweeper"), sweeps=sweeps, save_sweeps=True
        )
        next_sweep = sweeper.get_next()
        while next_sweep is not None:
            try:
                parameter_tuple, parameter_file = next_sweep
                parameter = {
                    "stressConso": parameter_tuple[0],
                    "idleConso": parameter_tuple[1],
                    "nameTechno": "lora" if "lora" in parameter_file else "nbiot",
                    "typeSynchro": parameter_tuple[2]
                }
                joined_params = simulation_functions.get_params_joined(parameter)
                title = Path(parameter_file).stem

                ## Designate parameter file and create result dir
                current_test_path=os.path.join(expe_esds_parameter_files,parameter_file)
                execution_dir = f"{title}-{joined_params}"
                os.makedirs(os.path.join(idle_results_dir, execution_dir), exist_ok=True)
                os.makedirs(os.path.join(reconf_results_dir, execution_dir), exist_ok=True)
                os.makedirs(os.path.join(sends_results_dir, execution_dir), exist_ok=True)
                os.makedirs(os.path.join(receive_results_dir, execution_dir), exist_ok=True)

                platform_path = os.path.abspath(f"concerto-d/platform-{joined_params}.yaml")
                platform_path_copy = os.path.abspath(f"concerto-d/platform-{joined_params}-{title}-{num_run}.yaml")
                shutil.copy(platform_path, platform_path_copy)

                with open(platform_path_copy) as f:
                    data = yaml.safe_load(f)
                with open(platform_path_copy, "w") as f:
                    data["nodes"]["arguments"]["all"]["expe_config_file"] = current_test_path
                    data["nodes"]["arguments"]["all"]["num_run"] = num_run
                    yaml.safe_dump(data, f, sort_keys=False)

                ## Launch experiment
                start_at = time.time()
                print(f"Starting {execution_dir}")
                # print(f"Starting experiment, platform_path_copy: {platform_path_copy}")
                # with open(os.path.join(root, f"logs/{execution_dir}-log.txt"), "w") as f:
                #     subprocess.run(["esds", "run", platform_path_copy], stdout=f, timeout=tests_timeout, encoding="utf-8")
                out = subprocess.check_output(["esds", "run", platform_path_copy], stderr=subprocess.STDOUT, timeout=tests_timeout, encoding="utf-8")
                # out = subprocess.Popen(["esds", "run", platform_path_copy], stderr=subprocess.STDOUT, encoding="utf-8")
                # out.wait()
                # if "AssertionError" in out:
                #     for line in out.split("\n"):
                #         if line.startswith("AssertionError"):
                #             print(line)
                end_at = time.time()
                print(f"Finished {title}")

                ## Run verification scripts
                with open(current_test_path) as f:
                    esds_parameters = yaml.safe_load(f)
                _esds_results_verification(esds_parameters, expe_esds_verification_files, idle_results_dir, reconf_results_dir,
                                           sends_results_dir, receive_results_dir, execution_dir, parameter["stressConso"],
                                           parameter["idleConso"])
                expe_duration = end_at - start_at
                print(f"{title} passed (%0.1fs)" % (expe_duration))
                sum_expes_duration += expe_duration

                ## Aggregate to global results
                result = {title: {"energy": _load_energetic_expe_results_from_title(execution_dir, idle_results_dir, reconf_results_dir,
                                                                                    sends_results_dir, receive_results_dir),
                                  "time": esds_parameters["max_execution_duration"]}}
                global_results_path = f"global_results-{title}-{joined_params}.yaml"
                with open(os.path.join(root, global_results_path), "w") as f:
                    yaml.safe_dump(result, f)
                sweeper.done(next_sweep)
                next_sweep = sweeper.get_next()
            except Exception as err:
                print(f"FAILED {next_sweep}")
                traceback.print_exc()
                sweeper.skip(next_sweep)
            finally:
                next_sweep = sweeper.get_next()
                print(f"Getting next sweeps: {next_sweep}")


if __name__ == '__main__':
    import sys
    simu_to_launch_dir = ""
    print(sys.argv)
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
