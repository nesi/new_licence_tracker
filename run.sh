#!/bin/bash

module load Python

./utils/merge_lic.py ./utils/_default_licences.yml ./utils/_licences.yml licences.yml
./licence_monitor.py 


