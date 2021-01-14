import ruamel.yaml as yaml # Fancy YAML parser to keep comments.
from clog import log
import subprocess

# To keep config as short as possible, only properties that differ from the norm need setting.
# This object should be able to be written back to YAML, *with comments* and no duplicate info.
class DDict(dict):
    """Dictionary with default value"""
    def __init__(self, _new_values, _default_values):
        self.new_values = _new_values
        self.default_values = _default_values

    def __getitem__(self, key):
        if key in self.new_values:
            return self.new_values[key]
        elif key in self.default_values:
            return self.default_values[key]
        else:
            print(f"Error. '{key}' is not a valid key.")
            return   

    def __setitem__(self, key, value):
        self.new_values[key]=value
        if key not in self.default_values:
            print(f"Error. '{key}' is not a valid key.")
        elif value != self.default_values[key]:
            self.new_values = value

def load_licences(config_path, defaults_path):
    """Loads yaml files and returns list of 'ddict' """
    licence = yaml.YAML().load(open(config_path))
    default_licence = yaml.YAML().load(open(defaults_path))[0]
    default_feature = default_licence["tracked_features"]["example_feature"]

    # Create list of DDicts.
    licences=list(map(lambda x: DDict(x, default_licence), licence))
    
    # Each tracked feature also needs defaults.
    for licence in licences:
        for key, feature in licence["tracked_features"].items():
            licence["tracked_features"][key]=DDict(feature,default_feature)
            # eww

    return licences

def load_conf(conf):
    return yaml.YAML().load(open(conf))

def run_cmd(cmd_string):
    log.debug(f"Running command '{cmd_string}'")
    
    #.strip().decode("utf-8", "replace")  # Removed .decode("utf-8") as threw error.
    
    sub_return = subprocess.run(cmd_string, shell=True, capture_output=True)
    stderr_txt=sub_return.stderr.decode('utf-8')
    stdout_txt=sub_return.stdout.decode('utf-8')
    if sub_return.returncode != 0:
        raise(Exception(f"Failed to run '{cmd_string}'. Returns error '{stderr_txt}\n{stdout_txt}'"))
    else:
        #log.debug(f"cmd output '{stdout_txt}'")
        return(stdout_txt)

# Got sick of implimenting this all the time.
def add_or_incriment(dic, keys, value):       
    """Assign to nested dic, e.g. 
    add_or_incriment(dic, ['key1', 'key2', 'key3'], value)
    {key1:{key2:{key3:1}}}
    """ 
    def desc(dic, i, value):
        if i < len(keys)-1:
            if keys[i] not in dic:
                dic[keys[i]] = {}
            desc(dic[keys[i]], i+1, value)            
        else:
            dic[keys[i]] = dic[keys[i]] + value if keys[i] in dic else value
    desc(dic, 0, value)


def time2seconds(time):
    """To allow reading of promethius time values"""
    unit_values = {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "y":31556952}
    return time if time[-1].isdigit() else int(time[:-1]) * unit_values[time[-1]]
     