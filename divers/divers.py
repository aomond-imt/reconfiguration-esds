import yaml
import os

actuals = sorted(os.listdir("esds-parameters-files-per-run/0/expe_esds_parameter_files_dao/actual"))
to_comp_lora = sorted([k for k in os.listdir("esds-parameters-files-per-run/0/expe_esds_parameter_files_dao/to_comp") if "lora" in k])
to_comp_nbiot = sorted([k for k in os.listdir("esds-parameters-files-per-run/0/expe_esds_parameter_files_dao/to_comp") if "nbiot" in k])


for f1, f2 in zip(to_comp_lora, actuals):
    with open(f"esds-parameters-files-per-run/0/expe_esds_parameter_files_dao/to_comp/{f1}") as f:
        actual = yaml.safe_load(f)
    with open(f"esds-parameters-files-per-run/0/expe_esds_parameter_files_dao/actual/{f2}") as f:
        to_comp = yaml.safe_load(f)
    res = round(abs(actual["max_execution_duration"] - to_comp["max_execution_duration"]), 2)
    if res > 3:
        print(actual["max_execution_duration"], to_comp["max_execution_duration"], res, f1.split("-")[:-1] == f2.replace(".yaml", "").split("-"), f1)
