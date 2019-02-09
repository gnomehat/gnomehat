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

from gnomehat import hostinfo

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
    except subprocess.CalledProcessError:
        print('Error: {} is not a git repository'.format(os.getcwd()))
        print('To use gnomehat, make sure your source code is checked into git')
        print('To initialize a git repository, use:')
        print('    git init .')
        print('    git add file1.py file2.py ...')
        print('    git commit')
        exit(1)

    # Shallow-clone the cwd repository to target_dir
    # This preserves branch name and commit hash, but skips history
    # Note: git-clone is finnicky and requires us to chdir to the target
    source_dir = os.getcwd()
    mkdirp(target_dir)
    os.chdir(target_dir)
    clone_cmd = ['git', 'clone', '--depth=1', 'file://{}'.format(source_dir), '.']
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


def build_start_sh(command, args):
    # TODO: Replace this with something more structured
    return '''#!/bin/bash
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi
script -q -c '{} {}' /dev/null
'''.format(command, args)


def chmodx(filename):
    st = os.stat(filename)
    os.chmod(filename, st.st_mode | stat.S_IEXEC)


# TODO: We don't want the default behavior of eg. argparse because of usage like:
#  gnomehat -m "my experiment" python train.py --arg1 --arg2
# We want to parse left-to-right UNTIL we hit something that looks like a command
def parse_args(argv):
    # Surely no one will ever want to run a --help command inside a worker process
    if '--help' in argv or len(argv) < 2:
        raise ValueError

    options = {
        'notes': '',
        'namespace': get_default_namespace(),
        'sourceless': False,
    }
    i = 1
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
        elif argv[i] in ['--sourceless']:
            options['sourceless'] = True
            i += 1
        elif i >= len(argv):
            # Missing command after 'gnomehat'
            raise ValueError
        else:
            options['executable'] = argv[i]
            options['args'] = argv[i+1:]
            break

    if options['executable'] in ['python', 'python3']:
        log('Executing Python script with args: {}'.format(options['args']))
        # TODO: run pyflakes maybe?
    return options


def get_user_settings():
    dotfile = os.path.expanduser('~/.gnomehat')
    if os.path.exists(dotfile):
        info = json.load(open(dotfile))
        return info
    return {}


def get_default_namespace():
    return get_user_settings().get('namespace', 'default')


def gnomehat_run(options):
    # Check the experiments directory
    experiments_dir = get_user_settings().get('experiments_dir')
    if experiments_dir is None:
        experiments_dir = input('Input an experiments directory:\n> ')
    namespace_dir = os.path.join(experiments_dir, options['namespace'])
    log('Adding experiment to {}'.format(namespace_dir))
    mkdirp(namespace_dir)

    # Create a copy of this experiment in target_dir
    experiment_name = make_experiment_name(namespace_dir)
    log('Creating target directory {}'.format(experiment_name))
    target_dir = os.path.join(namespace_dir, experiment_name)
    if not options['sourceless']:
        copy_repo(target_dir)

    # Write a .sh script containing the user-supplied command to be run
    os.chdir(target_dir)
    log('Creating {}/gnomehat_start.sh'.format(target_dir))
    command = options['executable']
    args = options['args']
    with open('gnomehat_start.sh', 'w') as fp:
        fp.write(build_start_sh(command, args))
    chmodx('gnomehat_start.sh')

    with open('gnomehat_notes.txt', 'w') as fp:
        fp.write(options['notes'])

    # TODO: Interactive Mode
    # Display a tmux-style info bar: "Press ctrl+T to run in background"
    # Open a connection to the worker and stream stdout/stderr

    # For now, always background the process
    gui_url = hostinfo.get_hostinfo(experiments_dir).get('gui_url')
    if gui_url:
        print("\nExperiment is now running at:")
        print("\t{}/experiment/{}/{}\n".format(gui_url, options['namespace'], experiment_name))
    else:
        print("Error: Cannot read {}/hostinfo.json, please restart server".format(namespace_dir))

