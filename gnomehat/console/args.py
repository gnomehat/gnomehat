import os
import stat
import sys
import uuid
import os
import subprocess
import shutil
import requests
import argparse
import json

STANDARD_COMMANDS = [
    'start',
    'stop',
    'restart',
    'status',
    'demo',
    'logs',
    'run',
]
SPECIAL_COMMANDS = [
    'python',
]


def print_usage():
    print('\n\t\tGnomehat: the simple experiment tracker')
    print('Command-line interface')
    print('\nUsage:')
    print('\tgnomehat start [experiments_dir]')
    print('\tgnomehat stop')
    print('\tgnomehat restart')
    print('\tgnomehat status')
    print('\tgnomehat logs')
    print('\tgnomehat doctor')
    print('\tgnomehat run [-n namespace] [-m message] <command...>')
    print('')
    print('start: Starts a gnomehat_server daemon and one gnomehat_worker per GPU')
    print('stop: Kills all gnomehat daemons on this machine')
    print('restart: Alias for gnomehat stop && gnomehat start')
    print('status: Prints all running gnomehat processes')
    print('logs: Tails log files for all gnomehat daemons')
    print('doctor: Checks for common configuration problems')
    print('run: Executes a shell command as a Gnomehat experiment. Requires an active server.')
    print('\t-n namespace: Optional namespace to organize experiments. Defaults to "default"')
    print('\t-m message: Optional comment string to remember why you ran this experiment')
    print('Note: "gnomehat python" is an alias to "gnomehat run python"')
    print('')


# Note that the following are both valid and equivalent:
# gnomehat run -m "my experiment" python main.py
# gnomehat -m "my experiment" python main.py
def parse_gnomehat_args(argv):
    for i in range(len(argv)):
        if argv[i] in STANDARD_COMMANDS:
            command = argv[i]
            remaining_args = argv[1:i] + argv[i+1:]
            break
        elif argv[i] in SPECIAL_COMMANDS:
            command = 'run'
            remaining_args = argv[1:]
            break
    else:
        raise ValueError('Invalid command')
    return command, remaining_args
