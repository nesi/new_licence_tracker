#!/usr/bin/env python3

import time
import yaml
import subprocess
from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, CollectorRegistry
from utils import poll_methods

#from clog import log

conf = yaml.load(open("./config.yml"), Loader=yaml.FullLoader)

class log():
    """Placeholder. Should be replaced with actual notification"""
    debug = info = warning = error = print

class LicenceCollector():
    # Represents all of the licence server for a given poll frequency.
    def __init__(self, licences):

        # Define the three main gauges.
        self.gauge_free = GaugeMetricFamily("flexlm_licenses_free", 'Unused license tokens', labels=[
                                            'institution', 'faculty', 'app', 'feature', 'token'])
        self.gauge_total = GaugeMetricFamily("flexlm_licenses_issued", 'Unused license tokens', labels=[
                                             'institution', 'faculty', 'app', 'feature', 'token'])
        self.gauge_used = GaugeMetricFamily("flexlm_licenses_used", 'Unused license tokens', labels=[
            'institution', 'faculty', 'app', 'feature', 'token', 'user', 'cluster', 'nodetype'])

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

if __name__ == '__main__':
    # Load licences, and defaults.
    licences = yaml.load(open(conf["licence_conf"]), Loader=yaml.FullLoader)

    # Common sense checks.
    if subprocess.check_output("whoami") != conf["user"]:
        log.warning(f"Run as {conf['user']} for read access on licences.")

    #TODO Some validation maybe?

    # Map each licence to relevent port.
    promethius_ports={}
    for licence in licences:
        if not licence["server_polling"]: continue # Skip disabled.
        if licence["promethius_port"] not in promethius_ports:
            promethius_ports[licence["promethius_port"]]=[]
        promethius_ports[licence["promethius_port"]].append(licence)

    # Run until interupt.
    try:
        for promethius_port, licences_on_port in promethius_ports.items():
            try:
                # Create registry and start server.
                registry_for_port = CollectorRegistry(auto_describe=True)
                log.info(
                    f"Starting polling {len(licences_on_port)} servers on Promethius port {promethius_port}")
                start_http_server(int(promethius_port), 'localhost', registry_for_port)
                registry_for_port.register(
                    LicenceCollector(licences_on_port))
            except Exception as e:
                log.error(f"Could not start promethius server {e}")
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("bye")