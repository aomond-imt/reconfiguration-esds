#!/usr/bin/env python

import os,subprocess,time,sys
import shutil

##### Setup variables
tests_timeout=20 # Max duration of a test
esds_data_dir = "/tmp/esds_generated_files"
esds_current_data_file = "/tmp/current_esds_config_file.yaml"

##### Run all experiments
for file in os.listdir(esds_data_dir):
    current_test_path=os.path.join(esds_data_dir,file)
    shutil.rmtree(esds_current_data_file, ignore_errors=True)
    shutil.copy(current_test_path, esds_current_data_file)

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
        exit()
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
