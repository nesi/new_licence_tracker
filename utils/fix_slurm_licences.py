#!/usr/bin/env python3

from NeSI.data import prometheus as P
import datetime
import time
import math
import sys
import yaml
import subprocess


class log():
    """Placeholder. Should be replaced with actual notification"""
    debug = info = warning = error = print


if __name__ == '__main__':

    # Step one. Validatconf_featuree user.
    slurm_permissions = subprocess.run(
        "sacctmgr show user ${USER} -Pn", shell=True, capture_output=True).stdout.decode('utf-8').strip().split("|")[-1].lower()
    if slurm_permissions == "administrator":
        log.debug("Running as slurm administrator")
    else:
        raise Exception("Not slurm admin")

    conf = yaml.load(open("./config.yml"), Loader=yaml.FullLoader)
    conf_licences = yaml.load(
        open(conf["licence_conf"]), Loader=yaml.FullLoader)

    for conf_licence in filter(lambda x: x["server_polling"], conf_licences):
        for conf_feature_name, conf_feature_values in conf_licence["tracked_features"].items():
            if not conf_feature_values["slurm_track"]:
                continue
            try:
                subprocess_return=subprocess.run(f"sacctmgr -i add resource Name={conf_feature_name.lower()} Server={conf_licence['licence_owner']} type=License count=1", shell=True, capture_output=True)            
                log.info((subprocess_return.stdout+subprocess_return.stderr).decode('utf-8').strip())

                actual_total = P.query(
                    f"sum(flexlm_licenses_issued{{feature=\"{conf_feature_name}\", owner=\"{conf_licence['licence_owner']}\"}})").max()

                rounded_count = int(
                    100 / len(conf_licence["allowed_clusters"]))
                meta_total = math.ceil(100*actual_total/rounded_count)

                subprocess_return=subprocess.run(
                    f"sacctmgr -i modify resource Name={conf_feature_name} Server={conf_licence['licence_owner']} Set Count={str(meta_total)} Description={conf_licence['software_name']}", shell=True, capture_output=True)
                log.info((subprocess_return.stdout+subprocess_return.stderr).decode('utf-8').strip())

                for cluster in conf_licence["allowed_clusters"]:
                    log.info(subprocess.run(
                        f"sacctmgr -i add resource set percentallowed={rounded_count} where name={conf_feature_name.lower()} server={conf_licence['licence_owner']} cluster={cluster}", shell=True, capture_output=True).stdout.decode('utf-8'))
            except ValueError:
                log.warning(
                    f"Couldn't contact promethius to find total for {conf_feature_name}@{conf_licence['licence_owner']}'")

        time.sleep(1)
    log.info(subprocess.run("sacctmgr show resource withclusters -n -p",
                            shell=True, capture_output=True).stdout.decode('utf-8'))
