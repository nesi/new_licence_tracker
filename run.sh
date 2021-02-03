#!/bin/bash

trap "kill $pids" exit

module load Python
#utils/prometheus   --web.listen-address=:9400  --config.file utils/prometheus.yml    &
#pids="$pids $!"

./merge_lic.py _default_licences.yml _licences.yml licences.yml
./licence_monitor.py 

wait $pids

