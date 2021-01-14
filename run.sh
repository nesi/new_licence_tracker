#!/bin/bash

trap "kill $pids" exit

module load Python
export LOGLEVEL=DEBUG
utils/prometheus  --web.listen-address=:9400  --config.file utils/prometheus.yml &
pids="$!"
python main.py &
pids="$pids $!"

wait $pids

