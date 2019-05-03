# Right now the UI is all based on data we read from the filesystem
# All that file IO should happen in this module
import time
import socket
import random
import base64
import datetime
import pickle
import flask
import json
import os
import sys
import pytz
import subprocess

from gnomehat.server import app, config

# TODO: Rest of world
TIMEZONE = 'US/Pacific'
DEFAULT_NAMESPACE = 'default'


# Every experiment is a directory within a namespace
# Each namespace is a top-level directory within EXPERIMENTS_DIR
def get_namespaces(url_prefix):
    ensure_default_namespace()

    namespaces = []
    for namespace in os.listdir(config['EXPERIMENTS_DIR']):
        path = os.path.join(config['EXPERIMENTS_DIR'], namespace)
        if path.startswith('.'):
            continue
        if not os.path.isdir(path):
            continue
        namespaces.append({
            'name': namespace,
            'url': os.path.join(url_prefix, namespace),
            'count': len(ls_directories(path)),
            'last_modified': timestamp_to_str(os.stat(path).st_mtime),
        })
    return namespaces


# At least one namespace (the default namespace) must always exist
def ensure_default_namespace():
    default_namespace_path = os.path.join(config['EXPERIMENTS_DIR'], DEFAULT_NAMESPACE)
    if not os.path.exists(default_namespace_path):
        os.mkdir(default_namespace_path)


def ls_directories(path):
    return [os.path.join(path, name)
            for name in os.listdir(path)
            if os.path.isdir(os.path.join(path, name))]


def get_results(files_url, namespace=None):
    experiments_dir = get_experiments_dir(namespace)
    result_dirs = get_result_dirs(experiments_dir)

    results = []
    for dir_path in result_dirs:
        experiment = experiment_from_filesystem(dir_path, files_url)
        if experiment is not None:
            results.append(experiment)
    return sorted(results, key=lambda x: x['last_modified_timestamp'], reverse=True)


# The experiments_dir contains subdirectories, each of which is a shallow clone
def get_experiments_dir(namespace=None):
    if namespace is None:
        return config['EXPERIMENTS_DIR']
    return os.path.join(config['EXPERIMENTS_DIR'], namespace)


def get_result_dirs(experiments_dir):
    # List all subdirectories
    result_dirs = [os.path.join(experiments_dir, r)
                   for r in os.listdir(experiments_dir)]
    result_dirs = [r for r in result_dirs if os.path.isdir(r)]

    # Return the most recent N results
    result_dirs.sort(key=os.path.getmtime)
    max_results = config['MAX_RESULTS_PER_PAGE']
    result_dirs = result_dirs[-max_results:]
    return result_dirs


def experiment_from_filesystem(dir_path, files_url):
    # TODO: parse this in a non-fragile way
    assert dir_path.startswith(config['EXPERIMENTS_DIR'])
    chop = len(config['EXPERIMENTS_DIR']) + 1
    experiment_id = dir_path[chop:]

    timestamp = int(os.path.getmtime(dir_path))

    started_at = datetime.datetime.fromtimestamp(timestamp).replace(tzinfo=pytz.timezone(TIMEZONE))
    full_path = os.path.join(config['EXPERIMENTS_DIR'], experiment_id)
    dir_contents = get_dir_contents(full_path)
    if 'gnomehat_start.sh' not in dir_contents:
        return None
    if 'gnomehat_hide' in dir_contents:
        return None

    image_url = default_image_url()
    last_modified_timestamp = started_at
    jpgs = [filename for filename in dir_contents if has_image_extension(filename)]
    if jpgs:
        def last_modified(x):
            try:
                return os.path.getmtime(os.path.join(full_path,x))
            except:
                return 0
        jpgs.sort(key=last_modified)
        last_modified_timestamp = last_modified(jpgs[-1])
        image_url = '{}/{}/{}'.format(files_url, experiment_id, jpgs[-1])

    running_job = os.path.exists(os.path.join(full_path, 'worker_lockfile'))
    finished_job = os.path.exists(os.path.join(full_path, 'worker_finished'))
    started_job = os.path.exists(os.path.join(full_path, 'worker_started'))
    broken_job = os.path.exists(os.path.join(full_path, 'worker_error'))
    color = 'orangeish'
    if finished_job:
        color = 'blueish'
    elif broken_job and not running_job:
        color = 'reddish'
    elif not started_job and not running_job:
        color = 'greenish'

    experiment_name = experiment_id[:-8]
    experiment_name = experiment_name.replace('_', ' ').replace('-', ' ').strip()
    experiment_name = experiment_name.title()

    headline = ""
    headline = get_command(full_path)

    notes = get_notes(experiment_id)
    if notes:
        subtitle = notes
    else:
        subtitle = stdout_last_n_lines(experiment_id, n=1)

    completion_stats = get_completion_stats(experiment_id)

    metrics_summary = {}
    metrics_summary_filename = os.path.join(dir_path, '.last_summary.json')
    if os.path.exists(metrics_summary_filename):
        metrics_summary = json.loads(open(metrics_summary_filename).read())

    if len(headline) > 128:
        headline = headline[:128] + '...'
    if len(subtitle) > 128:
        subtitle = subtitle[:128] + '...'

    result = {
        'experiment_name': experiment_name,
        'headline': headline,
        'subtitle': subtitle,
        'notes': notes,
        'completion_stats': completion_stats,
        'dir_name': experiment_id,
        'name': experiment_id.replace('_', ' '),
        'start_timestamp': timestamp,
        'last_modified_timestamp': timestamp,
        'started_at': started_at.strftime('%a %I:%M%p'),
        'finished': finished_job,
        'color': color,
        'image_url': image_url,
        'last_log_summary': get_log_summary(experiment_id),
        'metrics_summary': metrics_summary,
    }
    return result



def get_worker_count():
    # TODO: Get more information about workers: GPUs, etc
    def parse_worker_filename(filename):
        if not filename.endswith('.txt'):
            return None
        tokens = filename.replace('.txt', '').split('_')
        if len(tokens) != 3:
            return None
        return tokens[1], tokens[2]

    workers = []
    experiment_listings = os.listdir(config['EXPERIMENTS_DIR'])
    for filename in experiment_listings:
        parsed = parse_worker_filename(filename)
        if parsed:
            workers.append(parsed)
    return len(workers)


def get_server_title():
    return config.get('GNOMEHAT_SERVER_TITLE', 'Gnomehat Experiments')


def get_notes(dir_path):
    notes_filename = os.path.join(config['EXPERIMENTS_DIR'], dir_path, 'gnomehat_notes.txt')
    if os.path.exists(notes_filename):
        return open(notes_filename).read()
    return ''


def get_completion_stats(dir_path):
    summary_filename = os.path.join(config['EXPERIMENTS_DIR'], dir_path, '.last_summary.log')
    if not os.path.exists(summary_filename):
        return ''
    # Look for the TQDM line and parse it, if possible
    try:
        cmd = ['grep', '|.*|.*/.*\[.*\]', summary_filename]
        summary_line = str(subprocess.check_output(cmd), 'utf-8')
    except subprocess.CalledProcessError:
        return ''
    percentage_complete = summary_line.split('%')[0]
    elapsed_remaining = summary_line.split('[')[1].split(',')[0]
    time_elapsed, time_remaining = elapsed_remaining.split('<')
    return "{}% complete ({} remaining)".format(percentage_complete, time_remaining)


# TODO: hack; this should come from eg. worker_started
def get_command(dir_path):
    start_path = os.path.join(dir_path, 'gnomehat_start.sh')
    lines = open(start_path).readlines()
    if not lines:
        return ''
    SCRIPT_LEFT = "script -q -c '"
    SCRIPT_RIGHT = "' /dev/null"
    command = lines[-1].replace(SCRIPT_LEFT, '').replace(SCRIPT_RIGHT, "")
    return command


def stdout_last_n_lines(dir_name, n):
    stdout_path = os.path.join(config['EXPERIMENTS_DIR'], dir_name, 'stdout.txt')
    if not os.path.exists(stdout_path):
        return ''
    last_log_summary = subprocess.check_output(['tail', '-{}'.format(n), stdout_path])
    return last_log_summary.decode().strip()


def get_log_summary(dir_name):
    last_log_summary = 'No Logs Available'
    log_summary_path = os.path.join(config['EXPERIMENTS_DIR'], dir_name, '.last_summary.log')
    stdout_path = os.path.join(config['EXPERIMENTS_DIR'], dir_name, 'stdout.txt')
    if os.path.exists(log_summary_path):
        last_log_summary = open(log_summary_path).read()
    elif os.path.exists(stdout_path):
        last_log_summary = stdout_last_n_lines(dir_name, 8)
    return last_log_summary


def get_images(experiments_dir):
    files = get_dir_images(experiments_dir)

    # Group the files based on name before the timestamp
    groups = {}
    for f in files:
        if '_' in f:
            groupname = '_'.join(f.split('_')[:-1])
        else:
            groupname = 'misc'
        if groupname not in groups:
            groups[groupname] = []
        groups[groupname].append(f)
    return groups.items()


def has_image_extension(filename):
    return any(filename.endswith('.' + ext) for ext in config['IMAGE_EXTENSIONS'])


# TODO: Allow deeper search?
def get_dir_contents(dir_name):
    dir_contents = os.listdir(dir_name)
    for name in dir_contents:
        if not os.path.isdir(os.path.join(dir_name, name)):
            continue
        img_path = os.path.join(dir_name, name)
        if os.path.exists(img_path):
            images = os.listdir(img_path)
            dir_contents.extend([os.path.join(name, img) for img in images])
    return dir_contents


def get_dir_images(dir_name):
    files = get_dir_contents(dir_name)
    return [f for f in files if has_image_extension(f)]


def default_image_url():
    return os.path.join(flask.request.url_root, '/static/images/default.png')


def get_experiment_ids(experiments_dir):
    return [d for d in os.listdir(experiments_dir) if os.path.isdir(os.path.join(experiments_dir, d))]


def get_experiment_metrics(experiments_dir, experiment_id, number_format=None):
    filename = os.path.join(experiments_dir, experiment_id, '.last_summary.json')
    if os.path.exists(filename):
        items = json.load(open(filename))
        if number_format:
            for k in items:
                if isinstance(items[k], float):
                    items[k] = number_format % items[k]
        return items
    # No metrics available for this experiment
    return {}


def get_all_experiment_metrics(experiments_dir, namespace, include_notes=True, number_format='%.04f'):
    experiment_ids = get_experiment_ids(os.path.join(experiments_dir, namespace))
    metrics = {}
    for eid in experiment_ids:
        metrics[eid] = get_experiment_metrics(os.path.join(experiments_dir, namespace), eid, number_format)
        if include_notes:
            metrics[eid]['notes'] = get_notes(os.path.join(namespace, eid))
    return metrics


def get_directory_listing(full_path):
    # Serve a directory of filenames
    listing = []
    for filename in os.listdir(full_path):
        stat = os.stat(os.path.join(full_path, filename))
        listing.append({
            'name': filename,
            'size': stat.st_size,
            'last_modified': timestamp_to_str(stat.st_mtime),
        })
    listing.sort(key=lambda x: x['name'])
    return listing


def timestamp_to_str(timestamp):
    timestamp = int(timestamp)
    value = datetime.datetime.fromtimestamp(timestamp)
    value.replace(tzinfo=pytz.timezone(TIMEZONE))
    return value.strftime('%Y-%m-%d %H:%M:%S')

