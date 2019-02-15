#!/usr/bin/env python3
import json
import os
import sys
import subprocess
import socket
import time
import tempfile
from gnomehat import sysinfo
from gnomehat import server_config
from gnomehat.file_input import read_directory_name, read_option
from gnomehat.local_ip import get_local_ip
from gnomehat.console.args import print_usage, parse_gnomehat_args


def load_cli_config():
    config_path = os.path.expanduser('~/.gnomehat')
    try:
        cfg = json.loads(open(config_path).read())
    except:
        return {}
    return cfg


def write_cli_config(config):
    config_path = os.path.expanduser('~/.gnomehat')
    print('Saving JSON config {} to file {}'.format(config, config_path))
    old_config = load_cli_config()
    old_config.update(config)
    with open(config_path, 'w') as fp:
        fp.write(json.dumps(old_config, indent=2) + '\n')


def prompt_create_experiments_dir():
    ############## Command Line Interface Configuration ##########
    print('\n')
    print('Welcome to the GnomeHat Setup wizard.')
    print('It looks like this is your first time running gnomehat')
    print('(The EXPERIMENTS_DIR variable has not been set.)')
    print('\n')
    print('Please choose a directory where your experiments should be stored.')
    print('Enter a directory name (eg. /home/username/experiments)')
    experiments_dir = read_directory_name()
    print('\n')

    ############## Environment/Toolchain Configuration ################
    print('Checking for CUDA/CuDNN installation...')
    result = subprocess.run('gnomehat_doctor')

    print("")
    print('Which way would you like Gnomehat to run Python?')
    print("    (If you're not sure, select option #1)")
    print("")
    selection = read_option({
        'miniconda': 'Run Gnomehat with Python 3.6 at {}/env'.format(experiments_dir),
        'nothing': 'Use your current Python at: {}'.format(which_python()),
    })
    if selection == 'nothing':
        print('Gnomehat will use the current Python: {}'.format(which_python()))
    else:
        print('Installing Gnomehat-only Python to {}/env'.format(experiments_dir))
        install_miniconda_python(experiments_dir)
        print('Gnomehat will use Miniconda Python at {}'.format(experiments_dir))
    print("")


    ############## Server Configuration ##############
    config = server_config.get_config(experiments_dir)

    if os.environ.get('GNOMEHAT_SERVER_HOSTNAME'):
        config['GNOMEHAT_SERVER_HOSTNAME'] = os.environ.get('GNOMEHAT_SERVER_HOSTNAME')
    elif get_local_ip():
        config['GNOMEHAT_SERVER_HOSTNAME'] = get_local_ip()

    if os.environ.get('GNOMEHAT_PORT'):
        config['GNOMEHAT_PORT'] = int(os.environ.get('GNOMEHAT_PORT'))

    print("")
    print('Do you want to open the GnomeHat UI to your local network?')
    print("    (If you're not sure, select option #1)")
    print("")
    selection = read_option({
        'localhost': 'Open to this computer only at http://{}:{}'.format(
            'localhost', config['GNOMEHAT_PORT']),
        'open-network': 'Open port {1} to the local network at http://{0}:{1}'.format(
            config['GNOMEHAT_SERVER_HOSTNAME'], config['GNOMEHAT_PORT']),
    })
    if selection == 'localhost':
        gnomehat_bind_ip = '127.0.0.1'
        print('Gnomehat will serve locally on {}'.format(gnomehat_bind_ip))
    else:
        gnomehat_bind_ip = '0.0.0.0'
        print('Gnomehat is open to the network at {}'.format(gnomehat_bind_ip))
    config['GNOMEHAT_BIND_IP'] = gnomehat_bind_ip
    print("")

    if os.environ.get('GNOMEHAT_SERVER_TITLE'):
        config['GNOMEHAT_SERVER_TITLE'] = os.environ.get('GNOMEHAT_SERVER_TITLE')

    # Write server configuration
    server_config.write_config(experiments_dir, config)

    # Write client configuration
    print('Now using {} as the EXPERIMENTS_DIR'.format(experiments_dir))
    write_cli_config({'EXPERIMENTS_DIR': experiments_dir})
    return experiments_dir


def install_miniconda_python(experiments_dir):
    cmd = ['gnomehat_install_standalone_python', os.path.join(experiments_dir, 'env')]
    subprocess.run(cmd)


def which_python():
    return str(subprocess.check_output(['which', 'python']), 'utf').strip()

