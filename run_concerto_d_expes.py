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
    # list_files_sends = sorted(os.listdir(sends_results), key=lambda f_name: int(Path(f_name).stem))
    # list_files_receives = sorted(os.listdir(receive_results), key=lambda f_name: int(Path(f_name).stem))
    # for reconf_file, send_file, send_receives in zip(list_files_reconfs, list_files_sends, list_files_receives):
    for node_reconf_file in list_files_reconfs:
        with open(os.path.join(reconfs_results, node_reconf_file)) as f:
            results_reconf = yaml.safe_load(f)
        # with open(os.path.join(reconfs_results, send_file)) as f:
        #     results_send = yaml.safe_load(f)
        # with open(os.path.join(reconfs_results, send_receives)) as f:
        #     results_receive = yaml.safe_load(f)

        node_id = int(Path(node_reconf_file).stem)
        # print(f"-- Node {node_id}:")
        for key, val in results_reconf.items():
            # print(f"{key}: {val}")
            if key in ["tot_reconf_time", "max_execution_time"]:
                if key == "max_execution_time":
                    expected_val = round(verification["max_execution_duration"], 2)
                else:
                    expected_val = round(verification["reconf_periods"][node_id], 2)
                try:
                    # print(f"Assert {key}: {val} == {expected_val}", end="")
                    assert val == expected_val
                    # print(" success")
                except AssertionError as e:
                    print(f"key: {key} - val: {val} - expected: {expected_val}")
                    raise e


def main():
    # Setup variables
    tests_timeout=20 # Max duration of a test

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
    i = 0
    limit_expes = math.inf
    for parameter_file in os.listdir(expe_esds_parameter_files):
        ## Limit number of experiments
        if i >= limit_expes:
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
        print("- %-40s%s " % (parameter_file,"=>"),end='')
        try:
            ## Launch experiment
            start_at=time.time()
            out=subprocess.check_output(["esds", "run", platform_path],stderr=subprocess.STDOUT,timeout=tests_timeout,encoding="utf-8")
            if "AssertionError" in out:
                for line in out.split("\n"):
                    if line.startswith("AssertionError"):
                        print(line)
            end_at=time.time()

            ## Run verification scripts
            _esds_results_verification(expe_esds_verification_files, reconf_results_dir, sends_results_dir, receive_results_dir, title)
            print("passed (%0.1fs)" % (end_at - start_at))

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
            i += 1


if __name__ == '__main__':
    main()
