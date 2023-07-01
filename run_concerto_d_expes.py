#!/usr/bin/env python

import os,subprocess,time,sys
import shutil

import yaml

##### Setup variables
tests_timeout=20 # Max duration of a test
esds_data_dir = "/tmp/esds_generated_files"
esds_current_data_file = "/tmp/current_esds_config_file.yaml"
results_dir = "/tmp/results"

# i = 0
##### Run all experiments
for file in os.listdir(esds_data_dir):
    current_test_path=os.path.join(esds_data_dir,file)
    shutil.rmtree(esds_current_data_file, ignore_errors=True)
    shutil.copy(current_test_path, esds_current_data_file)
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
        # if i > 2:
        #     break
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
    # finally:
    #     i += 1

extracted_exec_time_per_expe = {}

# List results
for expe_dir in os.listdir(results_dir):
    print(f"---- {expe_dir} -----")
    abs_expe_dir = os.path.join(results_dir, expe_dir)
    for file_name in sorted(os.listdir(abs_expe_dir), key=lambda f_name: int(f_name.split(".")[0])):
        abs_file_name = os.path.join(abs_expe_dir, file_name)
        with open(abs_file_name) as f:
            res = yaml.safe_load(f)
        node_id = file_name.split('.')[0]
        print(f"-- Node {node_id}:")
        for key, val in res.items():
            print(f"{key}: {val}")
            if node_id == "0" and key == "max_execution_time":
                extracted_exec_time_per_expe[expe_dir] = val
    print()

for key, val in extracted_exec_time_per_expe.items():
    print(f"{key}: {val}")
