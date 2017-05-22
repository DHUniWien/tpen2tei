import os
import sys
import yaml

def config ():
    CONFIG_FILE = "./tests/config.yaml"

    if not os.path.isfile (CONFIG_FILE):
        sys.exit('No configuration file found')

    with open (CONFIG_FILE, 'r') as cfg:
        # might throw ScannerError
        config = yaml.load (cfg)

        if 'settings' not in config:
            sys.exit ('No default configuration found')

        return config['settings']
