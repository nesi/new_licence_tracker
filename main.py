import utils
import poll_methods
import time
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, CollectorRegistry
from clog import log

conf = utils.load_yaml("./config.yml")
conf_prom = utils.load_yaml(conf["promethius_conf"])


class LicenceCollector():
    # Represents all of the licence server for a given poll frequency.
    def __init__(self, licences):

        # Define the three main gauges.
        self.gauge_free = GaugeMetricFamily("flexlm_licenses_free", 'Unused license tokens', labels=[
                                            'institution', 'faculty', 'app', 'feature', 'token'])
        self.gauge_total = GaugeMetricFamily("flexlm_licenses_issued", 'Unused license tokens', labels=[
                                             'institution', 'faculty', 'app', 'feature', 'token'])
        self.gauge_used = GaugeMetricFamily("flexlm_licenses_used", 'Unused license tokens', labels=[
                                             'institution', 'faculty', 'app', 'feature', 'token','user', 'cluster', 'nodetype'])

        # Create an instance of the 'poller' class per licence server.
        self.licence_server_pollers = []
        for licence in licences:
            try:
                self.licence_server_pollers.append(getattr(poll_methods, licence["server_poll_method"])(
                    licence, self.gauge_free, self.gauge_total, self.gauge_used))
            except AttributeError:
                log.error(
                    f"There is no PollMethod named {licence['server_poll_method']} in 'poll_methods.py'")
                exit(1)

    # Collect method is called by promethius
    def collect(self):
        # Call each poller.
        for poller in self.licence_server_pollers:
            poller()
        for gauge in [self.gauge_free, self.gauge_total, self.gauge_used]:
            yield gauge

# TODO Some validation
def validate():
    # List of valid promethius 'jobs'
    prom_job_names = list(name["job_name"] for name in conf_prom["scrape_configs"])
    for server in licences:
        if server["server_prom_job"] not in prom_job_names:
                log.warning(f"'{server['server_prom_job']}' is not a valid promethuis job. See '{conf['promethius_conf']}'")
      
  #check(licence)
    return


if __name__ == '__main__':
    licences = utils.load_licences(
            conf["licence_conf"], conf["default_licence_conf"]) 
    try:  
    #if True:
        # Common sense checks.
        if utils.run_cmd("whoami").strip() != conf["user"]:
            log.warning(f"Run as {conf['user']} for read access on licences.")
        # Load licences, and defaults.
        licences = utils.load_licences(
            conf["licence_conf"], conf["default_licence_conf"]) 
        
        validate()

        for prom_job in conf_prom["scrape_configs"]:
            # Get list of all licences using this frequency.
            scrape_interval = prom_job["scrape_interval"] if ("scrape_interval" in prom_job) else conf_prom["global"]["scrape_interval"]
            licences_on_job = list(filter(lambda x: (
                (x["server_prom_job"] == prom_job["job_name"]) and (x["server_polling"])), licences))
            if not licences_on_job:
                log.debug("skipping empty frequency")
                continue
            if True:
            #try:
                # Create registry and start server.
                registry_for_interval = CollectorRegistry(auto_describe=True)
                [host, port] = prom_job["static_configs"][0]["targets"][0].split(":")
                log.info(f"Starting polling {len(licences_on_job)} servers at {scrape_interval} interval on Promethius port {port}")
                start_http_server(int(port), host, registry_for_interval)
                registry_for_interval.register(LicenceCollector(licences_on_job))
            if False:
            #except Exception as e:
                log.error(f"Could not start promethius server {e}")

        while True:
            time.sleep(10)
    #if False:
    except KeyboardInterrupt:
        print("bye")
    # This is so awful.
        # for licence in licences:
        #     for feature, value in licence["tracked_features"].items():
        #         licence["tracked_features"][feature]=value.new_values       
        # utils.save_yaml(list(map(lambda x: x.new_values,licences)),conf["licence_conf"])

