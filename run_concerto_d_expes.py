#!/usr/bin/env python
import os,subprocess,time
import shutil
import traceback
from pathlib import Path

import yaml

OFF_POWER = 0
ON_POWER = 0.4
PROCESS_POWER = 1  # TODO model energetic
LORA_POWER = 0.16

NB_NODES = 6


def _esds_results_verification(expe_esds_verification_files, reconf_results_dir, sends_results_dir, receive_results_dir, title):
    # Retrieve verification file for the given configuration file
    verification = None
    for verif_file in os.listdir(expe_esds_verification_files):
        if Path(verif_file).stem == title:
            abs_verif_file = os.path.join(expe_esds_verification_files, verif_file)
            with open(abs_verif_file) as f:
                verification = yaml.safe_load(f)

    # Retrieve results files for reconfs, sends and receives
    reconfs_results = os.path.join(reconf_results_dir, title)
    sends_results = os.path.join(sends_results_dir, title)
    receive_results = os.path.join(receive_results_dir, title)

    list_files_reconfs = sorted(os.listdir(reconfs_results), key=lambda f_name: int(Path(f_name).stem))
    list_files_sends = sorted(os.listdir(sends_results), key=lambda f_name: int(Path(f_name).stem))
    list_files_receives = sorted(os.listdir(receive_results), key=lambda f_name: int(Path(f_name).stem))
    for node_reconf_file, node_send_file, node_receive_file in zip(list_files_reconfs, list_files_sends, list_files_receives):
        with open(os.path.join(reconfs_results, node_reconf_file)) as f:
            results_reconf = yaml.safe_load(f)
        with open(os.path.join(sends_results, node_send_file)) as f:
            results_send = yaml.safe_load(f)
        with open(os.path.join(receive_results, node_receive_file)) as f:
            results_receive = yaml.safe_load(f)

        # Verification reconfs
        ## Reconf duration
        node_id = int(Path(node_reconf_file).stem)
        for key, val in results_reconf.items():
            if key in ["tot_reconf_time", "max_execution_time"]:
                if key == "max_execution_time":
                    expected_val = round(verification["max_execution_duration"], 2)
                else:
                    expected_val = round(verification["reconf_periods"][node_id], 2)
                try:
                    assert val == expected_val
                except AssertionError as e:
                    print(f"key: {key} - val: {val} - expected: {expected_val}")
                    raise e

        ## Reconf energy cost
        key = "node_conso"
        val = (results_reconf["tot_reconf_time"] * PROCESS_POWER
               + results_reconf["tot_reconf_flat_time"] * ON_POWER
               + results_reconf["tot_no_reconf_time"] * ON_POWER)
        expected_val = float(results_reconf["node_conso"][:-1])
        try:
            assert round(val, 2) == round(expected_val, 2)
        except AssertionError as e:
            print(f"key: {key} - val: {val} - expected: {expected_val}")
            raise e

        # Verification sending durations
        for key, val in results_send.items():
            if key in ["tot_sending_flat_time"]:
                verif_sending_periods = verification["sending_periods"][node_id]
                for conn_id, expected_val in verif_sending_periods.items():
                    val_conn_id = round(val[conn_id], 2)
                    expected_val_conn_id = round(expected_val, 2)
                    try:
                        assert val_conn_id == expected_val_conn_id
                    except AssertionError as e:
                        print(f"key: {key} - val: {val} - expected: {verif_sending_periods}")
                        raise e

        # Verification receive durations
        for key, val in results_receive.items():
            if key in ["tot_receiving_flat_time"]:
                verif_receive_periods = verification["receive_periods"][node_id]
                for conn_id, expected_val in verif_receive_periods.items():
                    val_conn_id = round(val[conn_id], 2)
                    expected_val_conn_id = round(expected_val, 2)
                    try:
                        assert val_conn_id == expected_val_conn_id
                    except AssertionError as e:
                        print(f"key: {key} - val: {val} - expected: {verif_receive_periods}")
                        raise e


def _load_energetic_expe_results_from_title(title, reconf_results_dir, sends_results_dir, receive_results_dir):
    # Retrieve results files for reconfs, sends and receives
    reconfs_results = os.path.join(reconf_results_dir, title)
    sends_results = os.path.join(sends_results_dir, title)
    receive_results = os.path.join(receive_results_dir, title)

    list_files_reconfs = sorted(os.listdir(reconfs_results), key=lambda f_name: int(Path(f_name).stem))
    list_files_sends = sorted(os.listdir(sends_results), key=lambda f_name: int(Path(f_name).stem))
    list_files_receives = sorted(os.listdir(receive_results), key=lambda f_name: int(Path(f_name).stem))

    energetic_results_expe = {"reconfs": {}, "sendings": {}, "receives": {}}
    for node_reconf_file, node_send_file, node_receive_file in zip(list_files_reconfs, list_files_sends, list_files_receives):
        with open(os.path.join(reconfs_results, node_reconf_file)) as f:
            results_reconf = yaml.safe_load(f)
        with open(os.path.join(sends_results, node_send_file)) as f:
            results_send = yaml.safe_load(f)
        with open(os.path.join(receive_results, node_receive_file)) as f:
            results_receive = yaml.safe_load(f)
        node_id = int(Path(node_reconf_file).stem)
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
    reconf_results_dir = os.path.join(results_dir, "reconfs")
    sends_results_dir = os.path.join(results_dir, "sends")
    receive_results_dir = os.path.join(results_dir, "receives")

    # Start experiments
    ## Clean previous results dirs
    shutil.rmtree(results_dir, ignore_errors=True)

    ## Run all experiments
    # limit_expes = math.inf
    limit_expes = 5
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
            _esds_results_verification(expe_esds_verification_files, reconf_results_dir, sends_results_dir, receive_results_dir, title)
            expe_duration = end_at - start_at
            print("passed (%0.1fs)" % (expe_duration))
            sum_expes_duration += expe_duration

            ## Aggregate to global results
            global_results[title] = _load_energetic_expe_results_from_title(title, reconf_results_dir, sends_results_dir, receive_results_dir)
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

    print(f"All passed in {sum_expes_duration:.2f}s")

    print(" ------------ Results --------------")
    for key, nodes_results in global_results.items():
        print(f"{key}:")
        print(f"reconfs: {nodes_results['reconfs']}")
        print(f"sendings: {nodes_results['sendings']}")
        print(f"receives: {nodes_results['receives']}")
    print("------------------------------------")


if __name__ == '__main__':
    main()
