#!/bin/bash
module load Python
utils/prometheus --config.file utils/prometheus.yml &
python main.py &

