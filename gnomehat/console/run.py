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

from gnomehat import server_config
from gnomehat.console.wizard import load_cli_config
from gnomehat.file_input import read_directory_name

USAGE = '''
gnomehat_run: Run a shell command as a Gnomehat experiment

Usage:
    gnomehat_run [-m "message"] [-n namespace] <command ...>

Examples:
    gnomehat python main.py
    gnomehat python my_experiment_with_args.py --arg1 foo --arg2 bar
    gnomehat -m "Add frob layers" python main.py --frob=True
'''

verbose = False
def log(*args, **kwargs):
    if verbose:
        print(*args, **kwargs)


# TODO: proper logging everywhere
def enable_verbose_logging():
    global verbose
    verbose = True
    log('Verbose logging enabled')


def mkdirp(path):
    os.makedirs(path, exist_ok=True)


def make_experiment_name(experiment_dir):
    repository_name = os.getcwd().split('/')[-1]
    random_hex = uuid.uuid4().hex[:8]
    return '{}_{}'.format(repository_name, random_hex)


def make_target_dir(experiments_dir, experiment_name):
    return os.path.join(experiments_dir, experiment_name)


def copy_repo(target_dir):
    log('Copying current working repository to {}'.format(target_dir))
    # Check that this is a git repository
    try:
        subprocess.check_output(['git', 'describe', '--always'])
        repo_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'])
        repo_root = str(repo_root, 'utf-8').strip()
        print('Discovered repository root at {}'.format(repo_root))
    except subprocess.CalledProcessError:
        print('Error: {} is not a git repository'.format(os.getcwd()))
        print('To use gnomehat, make sure your source code is checked into git')
        print('To initialize a git repository, use:')
        print('    git init .')
        print('    git add file1.py file2.py ...')
        print('    git commit')
        exit(1)

    # Find the root directory of this repo, and our cwd relative to it
    unmatched_prefix, _, relative_cwd = os.getcwd().partition(repo_root)
    if unmatched_prefix:
        print('Warning: repository root directory does not match cwd, check symbolic links')

    # Shallow-clone the cwd repository to target_dir
    # This preserves branch name and commit hash, but skips history
    # Note: git-clone is finnicky and requires us to chdir to the target
    source_dir = os.getcwd()
    mkdirp(target_dir)
    os.chdir(target_dir)
    clone_cmd = ['git', 'clone', '--depth=1', 'file://{}'.format(repo_root), '.']
    subprocess.check_output(clone_cmd, stderr=subprocess.STDOUT)
    os.chdir(source_dir)

    # Get all potential untracked files in the current repo
    stdout = subprocess.check_output(['git', 'ls-files'])
    filenames = str(stdout, 'utf-8').splitlines()

    # Copy all untracked changes into target_dir
    for src_filename in filenames:
        dst_filename = os.path.join(target_dir, src_filename)
        mkdirp(os.path.dirname(dst_filename))
        shutil.copy2(src_filename, dst_filename)
    log('Copied {} files to {}'.format(len(filenames), target_dir))
    return relative_cwd


START_SH_TEMPLATE = '''#!/bin/bash
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi
cd ./{}
script -q -c '{} {}' /dev/null
'''
def build_start_sh(relative_cwd, command, args):
    return START_SH_TEMPLATE.format(relative_cwd, command, ' '.join(args))


def chmodx(filename):
    st = os.stat(filename)
    os.chmod(filename, st.st_mode | stat.S_IEXEC)


# TODO: We don't want the default behavior of eg. argparse because of usage like:
#  gnomehat -m "my experiment" python train.py --arg1 --arg2
# We want to parse left-to-right UNTIL we hit something that looks like a command
def parse_args(argv):
    options = {
        'notes': '',
        'namespace': get_default_namespace(),
        'ignore-git': False,
        'delete-when-finished': False,
        'hide-from-ui': False,
    }
    i = 0
    while True:
        if argv[i] in ['-m', '--message']:
            options['notes'] = argv[i+1]
            i += 2
        elif argv[i] in ['-n', '--namespace']:
            options['namespace'] = argv[i+1]
            i += 2
        elif argv[i] in ['-v', '--verbose']:
            enable_verbose_logging()
            i += 1
        elif argv[i] in ['--ignore-git']:
            options['ignore-git'] = True
            i += 1
        elif argv[i] in ['--hide-from-ui']:
            options['hide-from-ui'] = True
            i += 1
        elif argv[i] in ['--delete-when-finished']:
            options['delete-when-finished'] = True
            i += 1
        elif argv[i] == '--help':
            print(USAGE)
            exit(0)
        elif i >= len(argv):
            # Missing command after 'gnomehat'
            print(USAGE)
            exit(1)
        else:
            options['executable'] = argv[i]
            options['args'] = argv[i+1:]
            break

    if options['executable'] in ['python', 'python3']:
        log('Executing Python script with args: {}'.format(options['args']))
        # TODO: run pyflakes maybe?
    return options


def get_default_namespace():
    return load_cli_config().get('NAMESPACE', 'default')


def gnomehat_run(options):
    # Check the experiments directory
    experiments_dir = load_cli_config().get('EXPERIMENTS_DIR')
    if experiments_dir is None:
        experiments_dir = read_directory_name('Input an experiments directory:\n> ')
    namespace_dir = os.path.join(experiments_dir, options['namespace'])
    log('Adding experiment to {}'.format(namespace_dir))
    mkdirp(namespace_dir)

    # Create a copy of this experiment in target_dir
    experiment_name = make_experiment_name(namespace_dir)
    log('Creating target directory {}'.format(experiment_name))
    target_dir = os.path.join(namespace_dir, experiment_name)
    if options['ignore-git']:
        mkdirp(target_dir)
        repo_relative_cwd = '.'
    else:
        repo_relative_cwd = copy_repo(target_dir)

    # Write a .sh script containing the user-supplied command to be run
    os.chdir(target_dir)
    log('Creating {}/gnomehat_start.sh'.format(target_dir))
    command = options['executable']
    args = options['args']
    with open('gnomehat_start.sh', 'w') as fp:
        fp.write(build_start_sh(repo_relative_cwd, command, args))
    chmodx('gnomehat_start.sh')

    with open('gnomehat_notes.txt', 'w') as fp:
        fp.write(options['notes'])

    if options['delete-when-finished']:
        open('gnomehat_delete_when_finished', 'w').close()

    if options['hide-from-ui']:
        open('gnomehat_hide', 'w').close()

    # TODO: Interactive Mode
    # Display a tmux-style info bar: "Press ctrl+T to run in background"
    # Open a connection to the worker and stream stdout/stderr

    # For now, always background the process
    config = server_config.get_config(experiments_dir)
    gui_url = 'http://{}:{}'.format(config['GNOMEHAT_SERVER_HOSTNAME'], config['GNOMEHAT_PORT'])
    print("\nExperiment is now running at:")
    print("\t{}/experiment/{}/{}\n".format(gui_url, options['namespace'], experiment_name))

