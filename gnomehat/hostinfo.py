# The hostinfo.json file acts as a lockfile and a source of information for the server
import os
import json
import socket
import requests

DEFAULT_CONFIG = {
    'GNOMEHAT_SERVER_HOSTNAME': 'localhost',
    'GNOMEHAT_PORT': 8086,
    'GNOMEHAT_BIND_IP': '127.0.0.1',
    'GNOMEHAT_SERVER_TITLE': 'Gnomehat Experiments',
    'DEBUG': False,
    'MAX_RESULTS_PER_PAGE': 100,
    'IMAGE_EXTENSIONS': ['jpg', 'png', 'tiff', 'bmp', 'gif'],
}

def write_hostinfo(experiments_dir, config):
    filename = os.path.join(experiments_dir, 'hostinfo.json')
    with open(filename, 'w') as fp:
        fp.write(json.dumps(config, indent=2))
    print("Wrote hostinfo to {}".format(filename))


def get_hostinfo(experiments_dir):
    config = DEFAULT_CONFIG
    filename = os.path.join(experiments_dir, 'hostinfo.json')
    if os.path.exists(filename):
        config.update(json.load(open(filename)))
    config['EXPERIMENTS_DIR'] = experiments_dir
    return config


def server_ok(experiments_dir):
    hostinfo = get_hostinfo(experiments_dir)
    if hostinfo is None:
        return False
    url = 'http://{}:{}/'.format(hostinfo['GNOMEHAT_SERVER_HOSTNAME'], hostinfo['GNOMEHAT_PORT'])
    try:
        info = requests.get(url)
        return True
    except:
        return False
