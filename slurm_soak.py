from NeSI.data import prometheus as P
import datetime
import time
import math
import utils
from clog import log

conf = utils.load_yaml("./config.yml")

class Soak():
    def __init__(self):
        
        self.sacctmgr_licences = {}
        self.get_sacctmg_licences()

    def get_sacctmg_licences(self):
        "Parses the output of sacctmgr into dict"
        for line in utils.run_cmd("sacctmgr show resource withclusters -n -p").strip().split("\n"):
            ls = line.split("|")
            token_name=f"{ls[0]}@{ls[1]}"
            if token_name not in self.sacctmgr_licences:
                self.sacctmgr_licences[token_name] = {"feature":ls[0],"owner":ls[1], "count":int(ls[3]), "clusters":{}}
            self.sacctmgr_licences[token_name]["clusters"][ls[6]]=int(ls[7])
       
    def validate(self):
        """Checks for inconinosisinosistantancies"""
        # If licence config exists. Check against config.
        try:
            valid_sacctmgr_licences={}
            conf_licences = utils.load_licences(conf["licence_conf"], conf["default_licence_conf"])
            for conf_licence in filter(lambda x: x["server_polling"], conf_licences):
                for conf_feature_name, conf_feature_values in conf_licence["tracked_features"].items():
                    # try:
                    if not conf_feature_values["slurm_track"]: continue

                    slurm_token=f"{conf_feature_name.lower()}@{conf_licence['licence_owner']}"
                    log.debug(f"Slurm token is {slurm_token}")
                    
                    if slurm_token not in self.sacctmgr_licences:
                        log.warning(f"{slurm_token} is not a valid slurm token")
                        log.warning(f"sacctmgr add resource Name={conf_feature_name.lower()} Server={conf_licence['licence_owner']} type=License count=1")
                        continue

                    actual_total = P.query(f"sum(flexlm_licenses_issued{{feature=\"{conf_feature_name}\", owner=\"{conf_licence['licence_owner']}\"}})").max()

                    if math.isnan(actual_total): continue
                        
                    sacctmgr_total=self.sacctmgr_licences[slurm_token]["count"]
                    meta_total=self.count_metatotal(actual_total,len(conf_licence["allowed_clusters"]))
                    log.debug(f"{conf_feature_name} has actual total of {actual_total}, metatotal of {meta_total} and {sacctmgr_total} slurm tokens")
                    
                    if meta_total!=sacctmgr_total:
                        log.warning(f"{conf_feature_name} has {sacctmgr_total} slurm tokens, it should have {meta_total}.\nRun command 'sacctmgr modify resource -i Name={conf_feature_name} Server={conf_licence['licence_owner']} Set Count={str(meta_total)}'")
                    
                    if set(self.sacctmgr_licences[slurm_token]["clusters"].keys()) !=  conf_licence["allowed_clusters"]:    
                        log.warning("Cluster shares are wrong.") 
                        for cluster in conf_licence["allowed_clusters"]:
                            log.warning(f"sacctmgr modify resource set percentallowed={str(int(100 / len(conf_licence['allowed_clusters'])))} where name={conf_feature_name.lower()} server={conf_licence['licence_owner']} cluster={}")
                        
                        #log.warning(", ".join(self.sacctmgr_licences[slurm_token]["clusters"].keys()))
                        #log.warning(", ".join(conf_licence["allowed_clusters"]))

                        #TODO Acually Run fixes.
                        #raise Exception("eh")
                    valid_sacctmgr_licences[slurm_token]=self.sacctmgr_licences[slurm_token]
                    # except Exception as e:
                    #     continue
            self.sacctmgr_licences=valid_sacctmgr_licences
        except Exception as e:
            self.tracking = self.sacctmgr_licences

    def soak(self):
        for token_name, values in self.sacctmgr_licences.items():

            end = datetime.datetime.now()
            start = end - datetime.timedelta(minutes=20)
            free_licences = P.query(f"sum(flexlm_licenses_free{{feature=\"{values['feature']}\", owner=\"{values['feature']}\"}})", start=start, end=end, step="1m").max()

            for cluster, fraction in values["clusters"].items():
                total_tokens = (fraction * values["count"])/100
                used_tokens = max(P.query(f"sum(squeue_license_count{{feature=\"{values['feature']}\", owner=\"{values['feature']}\", cluster=\"{cluster}\"}})").max(),0)

                #used_tokens = max(P.query(f"sum(squeue_license_count{{feature=\"{values['feature']}\", owner=\"{values['owner']}\", cluster=\"{cluster}\"}})").max(),0)
                soak_count = total_tokens-free_licences-used_tokens
                print(total_tokens)
                print(free_licences)
                print(used_tokens)
                #print(soak_count)
        #soak=( free-tokens )

    def count_metatotal(self, count, div):
        # 'total * clusters' IS NOT THE SAME AS 'total / (1/clusters)'
        return math.ceil(100*count/(int(100 / div)))        





# Check total resources.


# start = end - datetime.timedelta(minutes=6000)

# feature="aa_r_hpc"
# owner="uoa_foe"
# data = P.query(f"sum(flexlm_licenses_issued{{feature=\"{feature}\", owner=\"{owner}\"}})")

# print(data.max())


# #!/bin/python

# import re
# import subprocess
# from clog import log
# import time
# import os
# import json

# def ex_slurm_command(sub_input, level="administrator"):
#     log.debug("Attempting to run SLURM command '" + sub_input + "'.")
#     if (level == "administrator" and slurm_permissions == "administrator") or (level == "operator" and (slurm_permissions == "operator" or slurm_permissions == "administrator")):
#         try:
#             output = subprocess.check_output(sub_input, shell=True).decode("utf-8")
#         except Exception as details:
#             raise Exception("Failed to execute SLURM command '" + sub_input + "':" + str(details))
#         else:
#             log.debug("Success!")
#             time.sleep(5)  # Avoid spamming database
#             return output
#     else:
#         with open("run_as_admin.sh", "a+") as f:
#             f.write(sub_input + "\n")
#         log.error("Writing command to 'run_as_admin.sh'")

#         raise Exception("User does not have appropriate SLURM permissions to run this command.")


# settings = readmake_json("settings.json")
# slurm_permissions="administrator"
# all_server_list = readmake_json("cache/licence_list.json")

# for server in all_server_list:
#     for feature in server["tracked_features"].values():
#         clusters = feature["clusters"].copy()
#         num_clust=len(feature["clusters"])
#         meta_total=num_clust * feature["total"]
#         fraction = int(100 / num_clust)
        
#         for token, values in lic_ar.items():
#             # List of clusters, remove once checked.           
#             if token == feature["token_name"]:

#                 if values[3] != meta_total:
#                     log.warning(token + " on " + values[6] + " has metatotal of " + str(values[3]) + " should have " + str(meta_total))

#                 if values[4] != fraction:
#                     log.warning(token + " on " + values[6] + " has fraction of " + str(values[4]) + " should have " + str(fraction))

#                 # If token from cluster not in list.
#                 if values[6] not in clusters:
#                     log.warning("slurm licence token assigned on cluster " + values[6] + " but not in licence controller")
#                     break
#                 clusters.remove(values[6])

#         if clusters:
#             for cluster in clusters:
#                 log.warning("sacctmgr add resource Name=" + values[0] + " Server=" + values[1] + "Clusters=" + cluster + " Count=" + str(meta_total) + " PercentAllowed=" + str(fraction))

# def apply_soak():
#     def _do_maths(feature):

#         log.debug("Doing maths...")
#         hour_index = datetime.datetime.now().hour - 1

#         feature["history"].append(feature["usage_all"])
#         while len(feature["history"]) > settings["history_points"]:
#             feature["history"].pop(0)

#         # Update average
#         if feature["hourly_averages"][hour_index]:
#             feature["hourly_averages"][hour_index] = round(
#                 ((feature["usage_all"] * settings["point_weight"]) + (feature["hourly_averages"][hour_index] * (1 - settings["point_weight"]))), 2
#             )
#         else:
#             feature["hourly_averages"][hour_index] = feature["usage_all"]

#         if not feature["slurm_active"]:
#             feature["token_soak"] = "--"
#             log.debug("Skipping  " + feature["feature_name"] + " disabled")
#         else:
#             feature["token_soak"] = int(min(max(max(feature["history"]), feature["usage_all"]) + feature["buffer_constant"], feature["total"]))

#     def _update_res(cluster, soak):
#         log.info("Attempting to update " + cluster + " reservation.")

#         sub_input = "scontrol update -M " + cluster + " ReservationName=" + res_name + " " + soak
#         ex_slurm_command(sub_input, "operator")

#     def _create_res(cluster, soak):
#         log.info("Attempting to update " + cluster + " reservation.")

#         sub_input = "scontrol create -M " + cluster + " ReservationName=" + res_name + " StartTime=now Duration=infinite Users=root Flags=LICENSE_ONLY " + soak
#         ex_slurm_command(sub_input)

#     if os.environ.get("SOAK", "").lower() == "false":
#         log.info("Licence Soak skipped due to 'SOAK=FALSE'")
#         return

#     log.info("Applying soak...")
#     res_name = "licence_soak"

#     res_update_strings = {}
#     for server in server_list:
#         for tracked_feature_name, tracked_feature_value in server["tracked_features"].items():

#             _do_maths(tracked_feature_value)

#             if not tracked_feature_value["slurm_active"]:
#                 log.debug(tracked_feature_name + "not slurm_active. Skipping...")
#                 continue
#             if not tracked_feature_value["token_name"]:
#                 log.debug(tracked_feature_name + "has no token name. Skipping...")
#                 continue

#             for cluster in tracked_feature_value["clusters"]:
#                 if tracked_feature_value["token_soak"]:
#                     if cluster not in res_update_strings:
#                         res_update_strings[cluster] = " licenses="
#                     res_update_strings[cluster] += tracked_feature_value["token_name"] + ":" + str(tracked_feature_value["token_soak"]) + ","

#         log.debug("Contructing reservation strings")
#         log.debug(json.dumps(res_update_strings))

#     for cluster, soak in res_update_strings.items():
#         if cluster not in settings["clusters"].keys() or "enabled" not in settings["clusters"][cluster].keys() or not settings["clusters"][cluster]["enabled"]:
#             log.info("Skipping licence soak on " + cluster)
#             continue
#         try:
#             _update_res(cluster, soak)

#         except Exception as details:
#             log.error("Reservation update failed: " + str(details))
#             log.info("Attempting to create new reservation.")
#             try:
#                 _create_res(cluster, soak)
#             except Exception as details:
#                 log.error("Failed to create reservation: " + str(details))
#             else:
#                 log.info("New reservation '" + res_name + "' created successfully.")
#         else:
#             log.info(cluster + " reservation updated successfully!")

#     schedul.enter(settings["squeue_poll_period"], 1, apply_soak)


if __name__ == '__main__':
    try:
        # Step one. Validatconf_featuree user.
        slurm_permissions=utils.run_cmd("sacctmgr show user ${USER} -Pn").strip().split("|")[-1].lower()
        if slurm_permissions=="administrator":
            log.debug("Running as slurm administrator")
        elif slurm_permissions=="operator":
            log.warning("Running as slurm operator, will not be able to create/delete reservations, or modify resources.")
        else:
            log.error(f"Must be run by a user with operator/administrator priviledges (currently {slurm_permissions})")
        
        s=Soak()
        s.validate()

        while True:
            loop_start = time.time()
            s.soak()
            time.sleep(max(conf["squeue_poll_period"]-(time.time() - loop_start),0))
    
    except KeyboardInterrupt:
        print("byeeeeeee")