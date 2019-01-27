# The hostinfo.json file acts as a lockfile and a source of information for the server
import os
import json
import socket
import requests
from gnomehat.local_ip import get_local_ip


def init_hostinfo(config):
    experiments_dir = config['EXPERIMENTS_DIR']
    port = config['GNOMEHAT_PORT']
    print("Generating {}/hostinfo.json".format(experiments_dir))

    # export GNOMEHAT_SERVER_URL=thismachine.mydomain.com to start a cluster
    if os.environ.get('GNOMEHAT_SERVER_URL'):
        hostname = os.environ.get('GNOMEHAT_SERVER_URL')
    else:
        hostname = get_local_ip()

    info = {
        'hostname': hostname,
        'port': port,
        'gui_url': 'http://{}:{}'.format(hostname, port),
        'experiments_dir': experiments_dir,
    }

    # export GNOMEHAT_SERVER_URL=thismachine.mydomain.com to start a cluster
    if os.environ.get('GNOMEHAT_SERVER_TITLE'):
        info['server_title'] = os.environ.get('GNOMEHAT_SERVER_TITLE')

    filename = os.path.join(experiments_dir, 'hostinfo.json')
    with open(filename, 'w') as fp:
        fp.write(json.dumps(info, indent=2))
    print("Wrote hostinfo to {}".format(filename))


def get_hostinfo(experiments_dir):
    filename = os.path.join(experiments_dir, 'hostinfo.json')
    if not os.path.exists(filename):
        return None
    return json.load(open(filename))


def server_ok(experiments_dir):
    hostinfo = get_hostinfo(experiments_dir)
    if hostinfo is None:
        return False
    url = 'http://{}:{}/info'.format(hostinfo['hostname'], hostinfo['port'])
    try:
        info = requests.get(url)
        return info
    except:
        return False
