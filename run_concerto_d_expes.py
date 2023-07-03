#!/usr/bin/env python
import math
import os,subprocess,time,sys
import shutil
from pathlib import Path

import yaml


def _esds_results_verification(expe_esds_verification_files, reconf_results_dir, sends_results_dir, receive_results_dir, title):
    reconfs_results = os.path.join(reconf_results_dir, title)
    sends_results = os.path.join(sends_results_dir, title)
    receive_results = os.path.join(receive_results_dir, title)
    # abs_expe_dir = os.path.join(results_dir, expe_dir)

    verification = None
    for verif_file in os.listdir(expe_esds_verification_files):
        if Path(verif_file).stem == title:
            abs_verif_file = os.path.join(expe_esds_verification_files, verif_file)
            with open(abs_verif_file) as f:
                verification = yaml.safe_load(f)

    list_files_reconfs = sorted(os.listdir(reconfs_results), key=lambda f_name: int(Path(f_name).stem))
    list_files_sends = sorted(os.listdir(sends_results), key=lambda f_name: int(Path(f_name).stem))
    # list_files_receives = sorted(os.listdir(receive_results), key=lambda f_name: int(Path(f_name).stem))
    for node_reconf_file, node_send_file in zip(list_files_reconfs, list_files_sends):
    # for node_reconf_file in list_files_reconfs:
        with open(os.path.join(reconfs_results, node_reconf_file)) as f:
            results_reconf = yaml.safe_load(f)
        with open(os.path.join(sends_results, node_send_file)) as f:
            results_send = yaml.safe_load(f)
        # with open(os.path.join(reconfs_results, send_receives)) as f:
        #     results_receive = yaml.safe_load(f)

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
    limit_expes = math.inf
    parameter_files_list = os.listdir(expe_esds_parameter_files)
    sum_expes_duration = 0
    nb_expes_tot = min(len(parameter_files_list), limit_expes)
    nb_expes_done = 0
    print(f"Total nb experiments: {nb_expes_tot}")
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

        platform_path=os.path.abspath("concerto-d/platform.yaml")
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
            print("Reason: "+str(err))
            exit(3)
        finally:
            nb_expes_done += 1

    print(f"All passed in {sum_expes_duration:.2f}s")


if __name__ == '__main__':
    main()