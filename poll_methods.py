from clog import log
import re
import utils

conf = utils.load_yaml("config.yml")

class PollMethod(object):
    """Each child class must include a '_yield_features() and '_yield_users()' method """

    def __init__(self, _licence, _gauge_free, _gauge_total, _gauge_used):
        self.licence = _licence

        self.gauge_free = _gauge_free
        self.gauge_total = _gauge_total
        self.gauge_used = _gauge_used

        self.failed_attempts = 0
        self.failed_attempt_threshold = conf["fail_tolerance"]

        # These patterns are used to identify NeSI resources. Compiled here for efficiency.
        self.patterns={}
        for cluster, values in conf["resources"].items():
            self.patterns[cluster] = re.compile(
                values["pattern"], flags=re.I)

    def __call__(self):
        # Check licence servers, catch failures.
        if self.failed_attempts >= self.failed_attempt_threshold:
            return
        try:
        #if True:
            for feature_match in self._yield_features():
                # Extract feature dictionary from regex match object
                feature_match_dict = feature_match.groupdict()                  
                # If there are tracked features, and this is one of them.
                if not self.licence["tracked_features"] or feature_match_dict["feature"] not in self.licence["tracked_features"]:
                    continue
                
                # Tags used by all of these metrics. 
                # (institution_short, faculty_short, software_name, feature, slurm_token_name)
                common_tags = ( self.licence["institution_short"], self.licence["faculty_short"], self.licence["software_name"], feature_match_dict["feature"], self.licence["tracked_features"][feature_match_dict["feature"]]["slurm_token_name"] )
                free=int(feature_match_dict['total']) - int(feature_match_dict['inuse'])
                total= int(feature_match_dict['total'])
                
                self.gauge_free.add_metric(common_tags, free)
                self.gauge_total.add_metric(common_tags, total)

                log.debug(feature_match_dict['feature'])
                log.debug(f"free: {str(free)}")
                log.debug(f"total: {str(total)}")

                # If recording users, do.
                if self.licence["server_track_users"]:
                    user_dict={"offsite_user":{"offsite_host":{"offsite_host":0}}}
                    user_matches = self._yield_users(feature_match_dict)
                    if user_matches:
                        for user_match in user_matches:
                            # Dictionary of 'user', 'host' key pairs.'user_match_dictionary' shorted to umd else line got really long.
                            umd = user_match.groupdict()
                            # If no number of licences specified, us '1'
                            count = int(
                                umd["count"]) if "count" in umd else 1
                            # For each match.
                            for cluster, pattern in self.patterns.items():
                                hostmatch=pattern.search(umd["host"])
                                if hostmatch:
                                    utils.add_or_incriment(user_dict, [umd["user"], cluster, hostmatch.group(0)], count)
                                    break
                            else:
                                user_dict["offsite_user"]["offsite_host"]["offsite_host"]+=count
                    for user, clusters in user_dict.items():
                        for cluster, nodetypes in clusters.items():
                            for nodetype, count in nodetypes.items():
                                self.gauge_used.add_metric(common_tags + ( user, cluster, nodetype ), count)
                    log.debug("used: " + str(user_dict))
                    # TODO update untracked dcitionary.
                #Reset attempts.
                self.failed_attempts = 0
        #if False:
        except Exception as e:
            self.failed_attempts += 1
            log.error(
                f"Could not poll server. {e}. Attempt ({self.failed_attempts}/{self.failed_attempt_threshold})")

    def _yield_features(self):
        """Should be implimented by child, returns an iterator of feature matches"""
        log.error(
            "This method should be extended by child and not called directly.")
        exit(1)

    def _yield_users(self, feature):
        """Should be implimented by child, takes feature as input and returns an iterator of feature matches"""
        log.error(
            "This method should be extended by child and not called directly.")
        exit(1)

class lmutil(PollMethod):
    """lmutil is the standard tool used to check flexlm licences"""

    def _yield_features(self):
        # TODO Match server details
        # First two imrtant lines, match first and return.
        # details_pattern1 = re.compile(
        #     r"License server status: (?P<port>.*)@(?P<cname>\S*)$", flags=re.M)
        # details_pattern2 = re.compile(
        #     r"^.* license server (?P<last_stat>.*) v(?P<version>.*)$", flags=re.M)

        feature_pattern = re.compile(
            r"^(?:Users of )*(?P<feature>\S+):  \(Total of (?P<total>\d+) license.? issued;  Total of (?P<inuse>\d*) license.? in use\)(?:\n\n.+\n.+\n(?P<userblok>(?:\n.+)*))?", flags=re.M)
        # User/host pattern
        cmd_string = f"utils/linx64/lmutil lmstat -a -c {self.licence['licence_file_path']}"
        cmd_out = utils.run_cmd(cmd_string)

        # TODO Match server details
        # details = { **details_pattern1.search(cmd_out).groupdict(), **details_pattern2.search(cmd_out).groupdict()}
        # log.debug("Server Misc: " + str(details)) def do_some_B_thing( self ):

        return feature_pattern.finditer(cmd_out)

    def _yield_users(self, feature):
        # If no users. Return none.
        if not feature["userblok"]:
            return None
        user_pattern = re.compile(
            r"^\s*(?P<user>\S*)\s(?P<host>\S*)\s.*", flags=re.M)

        return user_pattern.finditer(feature["userblok"])

class ansysli_util(PollMethod):
    """The method used to check ANSYS licence use"""

    def _yield_features(self):
        # Matches features
        feature_pattern = re.compile(
            r"Feature:[\s\S]*?FEATURENAME:\s(?P<feature>\S+)[\s\S]*?COUNT:\s(?P<total>\d+)[\s\S]*?USED:\s(?P<inuse>\d*)", flags=re.M)

        # ansysli_util doesn't treat licences normally.
        ansys_cmd_prefix = f"export ANSYSLMD_LICENSE_FILE=$(head -n 1 {self.licence['licence_file_path']} | sed -n -e 's/.*=//p');utils/linx64/ansysli_util"

        # Run printavail command and get output.
        cmd_out_feature = utils.run_cmd(f"{ansys_cmd_prefix} -printavail")

        # If tracking users, seperate command must be run.
        if self.licence["server_track_users"]:
            self.cmd_out_user = utils.run_cmd(f"{ansys_cmd_prefix} -liusage")

        return feature_pattern.finditer(cmd_out_feature)

    def _yield_users(self, feature):

        user_pattern = re.compile(
            r"^(?P<user>[A-Za-z0-9]*)@(?P<host>\S*)\:\d*\s+[\d\/]+\s[\d\:]+\s+" + feature["feature"] + r"\s+(?P<count>\d*)\s+.*$", flags=re.M)
        return user_pattern.finditer(self.cmd_out_user)
