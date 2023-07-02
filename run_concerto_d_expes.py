#!/usr/bin/env python
import math
import os,subprocess,time,sys
import shutil
from pathlib import Path

import yaml

##### Setup variables
tests_timeout=20 # Max duration of a test
expe_esds_parameter_files = "/tmp/expe_esds_parameter_files"
esds_current_parameter_file = "/tmp/current_esds_parameter_file.yaml"
results_dir = "/tmp/results"
expe_esds_verification_files = "/tmp/expe_esds_verification_files"

##### Clean dirs
shutil.rmtree(results_dir)

i = 0
limit_expes = math.inf
##### Run all experiments
for file in os.listdir(expe_esds_parameter_files):
    if i >= limit_expes:
        break
    current_test_path=os.path.join(expe_esds_parameter_files,file)
    shutil.rmtree(esds_current_parameter_file, ignore_errors=True)
    shutil.copy(current_test_path, esds_current_parameter_file)
    title = file.split(".")[0]
    os.makedirs(os.path.join(results_dir, title), exist_ok=True)

    platform_path=os.path.abspath("concerto-d/platform.yaml")
    print("- %-40s%s " % (file,"=>"),end='')
    try:
        start_at=time.time()
        out=subprocess.check_output(["esds", "run", platform_path],stderr=subprocess.STDOUT,timeout=tests_timeout,encoding="utf-8")
        if "AssertionError" in out:
            for line in out.split("\n"):
                if line.startswith("AssertionError"):
                    print(line)
        end_at=time.time()
        print("passed (%0.1fs)"%(end_at-start_at))
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

extracted_exec_time_per_expe = {}

# List and assert results
for expe_dir in os.listdir(results_dir):
    print(f"---- {expe_dir} -----")
    abs_expe_dir = os.path.join(results_dir, expe_dir)

    verification = None
    for verif_file in os.listdir(expe_esds_verification_files):
        if Path(verif_file).stem == expe_dir:
            abs_verif_file = os.path.join(expe_esds_verification_files, verif_file)
            with open(abs_verif_file) as f:
                verification = yaml.safe_load(f)

    for file_name in sorted(os.listdir(abs_expe_dir), key=lambda f_name: int(Path(f_name).stem)):
        abs_file_name = os.path.join(abs_expe_dir, file_name)
        with open(abs_file_name) as f:
            res = yaml.safe_load(f)
        node_id = int(Path(file_name).stem)
        print(f"-- Node {node_id}:")
        for key, val in res.items():
            print(f"{key}: {val}")
            if key in ["tot_reconf_time", "max_execution_time"]:
                if key == "max_execution_time":
                    expected_val = round(verification["max_execution_duration"], 2)
                else:
                    expected_val = round(verification[node_id], 2)
                try:
                    assert val == expected_val
                except AssertionError as e:
                    print(f"key: {key} - val: {val} - expected: {expected_val}")
                    raise e

            if node_id == 0 and key == "max_execution_time":
                extracted_exec_time_per_expe[expe_dir] = val
    print()

for key, val in extracted_exec_time_per_expe.items():
    print(f"{key}: {val}")
