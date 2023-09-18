#!/bin/bash
#hosts=$(echo $(oarstat -fu --json) | jq -r '.[].assigned_network_address[]')
#echo $hosts
set -e

#job_properties=$(oarstat -fu --json)
for h in $(echo $(oarstat -fu --json) | jq -r '.[].assigned_network_address[]'); do
  echo "Starting on host $h"
  ssh $h "tmux new-session -d 'cd ~/reconfiguration-esds && source venv/bin/activate && python3 run_concerto_d_expes.py expe_esds_parameter_files_dao'"
done
