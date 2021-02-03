#!/usr/bin/env python3

# Merges $1 and $2 into $3
# .yml

import sys
import yaml

class log():
    """Placeholder. Should be replaced with actual notification"""
    debug = info = warning = error = print

if __name__ == '__main__':
    if len(sys.argv) < 3: 
        raise Exception("Not enough inputs")

    default_licence = yaml.load(open(sys.argv[1]), Loader=yaml.FullLoader)[0]
    special_licences = yaml.load(open(sys.argv[2]), Loader=yaml.FullLoader)

    default_feature = default_licence["tracked_features"]["example_feature"]

    combind_licences = list(map(lambda x: {**default_licence, **x}, special_licences))

    # Each tracked feature also needs defaults.
    for licence in combind_licences:
        for key, feature in licence["tracked_features"].items():
            licence["tracked_features"][key]={**default_feature, **feature}
    with open(sys.argv[3], "w+") as f: 
        f.write(f"# This file was made by merging '{sys.argv[1]}' and '{sys.argv[1]}'.\n# DONT MAKE CHANGES HERE\n")
        yaml.dump(list(combind_licences), f, sort_keys=True)

