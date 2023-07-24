#!/usr/bin/env python
import os,subprocess,time
import shutil
import traceback
from pathlib import Path

import yaml

import print_results

OFF_POWER = 0
ON_POWER = 0.4
PROCESS_POWER = 1  # TODO model energetic
LORA_POWER = 0.16

NB_NODES = 6


def _assert_value(node_id, key, val, expected_val):
    try:
        assert round(val, 2) == round(expected_val, 2)
    except AssertionError as e:
        print(f"node_id: {node_id} - key: {key} - val: {val} - expected: {expected_val}")
        raise e


def _esds_results_verification(esds_parameters, expe_esds_verification_files, idle_results_dir, reconf_results_dir, sends_results_dir, receive_results_dir, title):
    # Retrieve verification file for the given configuration file
    verification = None
    for verif_file in os.listdir(expe_esds_verification_files):
        if Path(verif_file).stem == title:
            abs_verif_file = os.path.join(expe_esds_verification_files, verif_file)
            with open(abs_verif_file) as f:
                verification = yaml.safe_load(f)

    # Retrieve results files for reconfs, sends and receives
    idle_results = os.path.join(idle_results_dir, title)
    reconfs_results = os.path.join(reconf_results_dir, title)
    sends_results = os.path.join(sends_results_dir, title)
    receive_results = os.path.join(receive_results_dir, title)

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

        node_id = int(Path(node_idle_file).stem)
        max_exec_duration = esds_parameters["max_execution_duration"]

        # Verification idles
        node_uptimes = esds_parameters["uptimes_periods_per_node"][node_id]
        expected_uptime = sum(end-start for start, end in node_uptimes)
        expected_no_uptime = max_exec_duration - expected_uptime
        _assert_value(node_id, "tot_uptime", results_idle["tot_uptime"], expected_uptime)
        _assert_value(node_id, "tot_sleeping_time", results_idle["tot_sleeping_time"], expected_no_uptime)
        _assert_value(node_id, "node_conso", results_idle["node_conso"], expected_uptime*0.4)  # TODO magic value

        # Verification reconfs
        node_reconfs = esds_parameters["reconf_periods_per_node"][node_id]
        expected_reconf = sum((end-start)*nb_processes for start, end, nb_processes in node_reconfs)
        expected_reconf_flat = sum(end-start for start, end, nb_processes in node_reconfs if nb_processes > 0)
        expected_no_reconf_time = max_exec_duration - expected_reconf_flat
        expected_node_conso = sum((end-start)*nb_processes*PROCESS_POWER for start, end, nb_processes in node_reconfs)
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
        node_receives = esds_parameters["receive_periods_per_node"][node_id]
        expected_receive_flat_time = sum(end - start for start, end, node_send in node_receives if node_send != {})
        expected_no_receive_time = max_exec_duration - expected_receive_flat_time - expected_no_uptime
        _assert_value(node_id, "tot_receive_flat_time", results_receive["tot_receive_flat_time"], expected_receive_flat_time)
        _assert_value(node_id, "tot_no_receive_time", results_receive["tot_no_receive_time"], expected_no_receive_time)


def _load_energetic_expe_results_from_title(title, idle_results_dir, reconf_results_dir, sends_results_dir, receive_results_dir):
    # Retrieve results files for reconfs, sends and receives
    idle_results = os.path.join(idle_results_dir, title)
    reconfs_results = os.path.join(reconf_results_dir, title)
    sends_results = os.path.join(sends_results_dir, title)
    receive_results = os.path.join(receive_results_dir, title)

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
        energetic_results_expe["sendings"][node_id] = {"node_conso": results_send["node_conso"], "comms_cons": results_send["comms_cons"]}
        energetic_results_expe["receives"][node_id] = {"node_conso": results_receive["node_conso"], "comms_cons": results_receive["comms_cons"]}

    return energetic_results_expe


def main():
    # Setup variables
    tests_timeout=60 # Max duration of a test

    ## Configuration files dirs
    root = "/tmp"
    expe_esds_parameter_files = os.path.join(root, "expe_esds_parameter_files")
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
    shutil.rmtree(results_dir, ignore_errors=True)

    ## Run all experiments
    # limit_expes = math.inf
    limit_expes = 1
    parameter_files_list = os.listdir(expe_esds_parameter_files)
    sum_expes_duration = 0
    nb_expes_tot = min(len(parameter_files_list), limit_expes)
    nb_expes_done = 0
    print(f"Total nb experiments: {nb_expes_tot}")
    global_results = {}
    for parameter_file in parameter_files_list:
        ## Limit number of experiments
        if nb_expes_done >= limit_expes:
            break

        ## Designate parameter file and create result dir
        current_test_path=os.path.join(expe_esds_parameter_files,parameter_file)
        shutil.rmtree(esds_current_parameter_file, ignore_errors=True)
        shutil.copy(current_test_path, esds_current_parameter_file)
        title = Path(parameter_file).stem
        os.makedirs(os.path.join(idle_results_dir, title), exist_ok=True)
        os.makedirs(os.path.join(reconf_results_dir, title), exist_ok=True)
        os.makedirs(os.path.join(sends_results_dir, title), exist_ok=True)
        os.makedirs(os.path.join(receive_results_dir, title), exist_ok=True)

        platform_path = os.path.abspath("concerto-d/platform.yaml")
        print(f"{nb_expes_done+1}/{nb_expes_tot} - {parameter_file} => ", end="")
        try:
            ## Launch experiment
            start_at=time.time()
            out=subprocess.check_output(["esds", "run", platform_path],stderr=subprocess.STDOUT,timeout=tests_timeout,encoding="utf-8")
            # out = subprocess.Popen(["esds", "run", platform_path], stderr=subprocess.STDOUT, encoding="utf-8")
            # out.wait()
            if "AssertionError" in out:
                for line in out.split("\n"):
                    if line.startswith("AssertionError"):
                        print(line)
            end_at=time.time()

            ## Run verification scripts
            with open(current_test_path) as f:
                esds_parameters = yaml.safe_load(f)
            _esds_results_verification(esds_parameters, expe_esds_verification_files, idle_results_dir, reconf_results_dir, sends_results_dir, receive_results_dir, title)
            expe_duration = end_at - start_at
            print("passed (%0.1fs)" % (expe_duration))
            sum_expes_duration += expe_duration

            ## Aggregate to global results
            global_results[title] = _load_energetic_expe_results_from_title(title, idle_results_dir, reconf_results_dir, sends_results_dir, receive_results_dir)
        except subprocess.TimeoutExpired as err:
            print("failed :(")
            print("------------- Test duration expired (timeout="+str(tests_timeout)+"s) -------------")
            print(err.output,end="")
            exit(1)
        except subprocess.CalledProcessError as err:
            print("failed :(")
            print("------------- Test has a non-zero exit code -------------")
            print(err.output,end="")
            exit(2)
        except Exception as err:
            print("failed :(")
            traceback.print_exc()
            exit(3)
        finally:
            nb_expes_done += 1

    print("Dump results")
    with open(os.path.join(root, "global_results.yaml"), "w") as f:
        yaml.safe_dump(global_results, f)
    print("Results dumped")
    print(f"All passed in {sum_expes_duration:.2f}s")
    print_results.print_results()


if __name__ == '__main__':
    main()
