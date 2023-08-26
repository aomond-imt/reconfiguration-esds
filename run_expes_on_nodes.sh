#!/bin/bash

#set -e

## declare an array variable
declare -a parameters_to_launch=(
  "expe_esds_parameter_files_to_compute_1_2"
  "expe_esds_parameter_files_to_compute_3"
  "expe_esds_parameter_files_to_compute_4"
  "expe_esds_parameter_files_to_compute_5"
  "expe_esds_parameter_files_to_compute_10"
  "expe_esds_parameter_files_to_compute_15"
  "expe_esds_parameter_files_to_compute_20_T0"
  "expe_esds_parameter_files_to_compute_20_T1"
  "expe_esds_parameter_files_to_compute_25"
  "expe_esds_parameter_files_to_compute_30_deploy"
  "expe_esds_parameter_files_to_compute_30_update"
)
declare -a hosts=($(echo $(oarstat -fu --json) | jq -r '.[].assigned_network_address[]'))

#declare -a hosts=(
#  "gros-21"
#  "gros-22"
#  "gros-23"
#  "gros-24"
#  "gros-25"
#)

# get length of an array
hosts_length=${#hosts[@]}

# use for loop to read all values and indexes
for (( i=0; i<${hosts_length}; i++ ));
do
  echo "starting ${parameters_to_launch[$i]} on host ${hosts[$i]}"
  ssh ${hosts[$i]} "tmux kill-session -t $i"
  ssh ${hosts[$i]} "tmux new-session -d -s $i 'cd ~/reconfiguration-esds && source venv/bin/activate && python3 run_concerto_d_expes.py ${parameters_to_launch[$i]}'"
done
