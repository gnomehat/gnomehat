import time
import socket
import random
import base64
import datetime
import pickle
import flask
import json
import os
import rq
import sys
import pytz
import subprocess

from gnomehat import sysinfo, hostinfo
from gnomehat.server import app, arg, config


def get_files_url():
    return os.path.join(flask.request.url_root, 'experiments')


def default_image_url():
    return os.path.join(get_files_url(), 'kitty.jpg')


def websocket_host():
    host = flask.request.url_root.replace('http://', '').rstrip('/')
    host = host.split(':')[0]
    return host


@app.route('/')
def front_page():
    start_time = time.time()
    kwargs = {
        'results': get_results(),
    }
    print("Generated results for front page in {:.2f} sec".format(
        time.time() - start_time))
    return flask.render_template('index.html', **kwargs)


def get_results():
    results = []
    result_dirs = [os.path.join(config['EXPERIMENTS_DIR'], r) for r in os.listdir(config['EXPERIMENTS_DIR'])]
    result_dirs = [r for r in result_dirs if os.path.isdir(r)]
    result_dirs.sort(key=os.path.getmtime)
    result_dirs = result_dirs[-config['MAX_RESULTS']:]
    
    for dir_path in result_dirs:
        dir_name = dir_path.split('/')[-1]
        experiment_id = dir_name
        timestamp = int(os.path.getmtime(dir_path))

        started_at = datetime.datetime.fromtimestamp(timestamp).replace(tzinfo=pytz.timezone('US/Pacific'))

        full_path = os.path.join(config['EXPERIMENTS_DIR'], dir_name)

        dir_contents = get_dir_contents(full_path)

        image_url = default_image_url()
        last_modified_timestamp = started_at
        jpgs = [filename for filename in dir_contents if has_image_extension(filename)]
        if jpgs:
            def last_modified(x):
                return os.path.getmtime(os.path.join(full_path,x))
            jpgs.sort(key=last_modified)
            last_modified_timestamp = last_modified(jpgs[-1])
            image_url = '{}/{}/{}'.format(get_files_url(), dir_name, jpgs[-1])

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

        is_experiment = 'start.sh' in dir_contents

        experiment_name = experiment_id.split('_')[0]
        headline = experiment_name.title()
        if is_experiment:
            start_path = os.path.join(full_path, 'start.sh')
            lines = open(start_path).readlines()
            # TODO: hack; this should come from eg. worker_started
            headline = lines[-1].replace('stdbuf -i0 -o0 -e0', '')

        params = get_params(dir_path)
        if 'hypothesis' in params:
            subtitle = params['hypothesis']
        else:
            subtitle = stdout_last_n_lines(dir_name, n=2)
            if len(subtitle) > 128:
                subtitle = subtitle[:128] + '...'

        result = {
            'headline': headline,
            'subtitle': subtitle,
            'dir_name': dir_name,
            'name': experiment_id.replace('_', ' '),
            'start_timestamp': timestamp,
            'last_modified_timestamp': timestamp,
            'started_at': started_at.strftime('%a %I:%M%p'),
            'finished': finished_job,
            'params': get_params(dir_path),
            'color': color,
            'image_url': image_url,
            'last_log_summary': get_log_summary(dir_name),
            'is_experiment': is_experiment,
        }

        results.append(result)
    return sorted(results, key=lambda x: x['last_modified_timestamp'], reverse=True)


def get_params(dir_path, text=False):
    params = {}
    params_filename = os.path.join(dir_path, 'params.json')
    if os.path.exists(params_filename):
        params = json.load(open(params_filename))
    if text:
        return json.dumps(params, indent=2)
    return params


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


@app.route('/static/<path:path>')
def static_file(path):
    return flask.send_from_directory(app.static_folder, path)


@app.route('/experiments/<path:path>')
def static_experiments_file(path):
    return flask.send_from_directory(config['EXPERIMENTS_DIR'], path)


@app.route('/delete_job', methods=['POST'])
def delete_job():
    print("Delete job: {}".format(flask.request.get_json()))
    job_id = flask.request.get_json()['id']
    dir_name = os.path.join(config['EXPERIMENTS_DIR'], job_id)
    print("Delete {}".format(job_id))
    print("Removing {}".format(dir_name))
    # TODO: security lol
    import shutil
    shutil.rmtree(dir_name)
    return 'OK'


@app.route('/info')
def get_info():
    info = hostinfo.get_hostinfo(config['EXPERIMENTS_DIR'])
    return json.dumps(info, indent=2)


@app.route('/experiment/<experiment_id>')
def view_experiment(experiment_id):
    dir_path = os.path.join(config['EXPERIMENTS_DIR'], experiment_id)
    image_groups = []

    print('get_images output for {}:\n{}'.format(experiment_id, get_images(experiment_id)))
    for name, images in get_images(experiment_id):
        url_latest_n = []
        for image in sorted(images)[-5:]:
            url = '{}/{}/{}'.format(get_files_url(), experiment_id, image)
            url_latest_n.append(url)
        
        image_groups.append({
            'name': name,
            'url_latest_5': url_latest_n,
            'url_latest': url_latest_n[-1],
        })
    image_groups.sort(key=lambda x: x['name'])

    # When this page is viewed, spawn a websocketd
    port = spawn_console_websocket(os.path.join(dir_path, 'stdout.txt'))

    kwargs = {
        'experiment_id': experiment_id,
        'image_groups': image_groups,
        'last_log': get_log_summary(experiment_id),
        'parameters': get_params(dir_path, text=True),
        'websocket_host': websocket_host(),
        'websocket_port': port,
    }
    return flask.render_template('experiment.html', **kwargs)


# Tail -f the given filename in a websocket process
# Return the port number of the running websocketd
def spawn_console_websocket(filename):
    # Clean up any previous unused sockets for this experiment
    # TODO: something much much more sophisticated
    os.system('pkill -f websocketd')

    portnum = random.randint(20000, 29999)
    # TODO proper input sanitizing and process pool and resource management and and ...
    cmd = 'websocketd --port {:d} stdbuf -i0 -o0 -e0 tail -n 100 -f {} &'.format(portnum, filename)
    print("Running {}".format(cmd))
    os.system(cmd)
    return portnum


def get_images(experiment_id):
    experiments_dir = os.path.join(config['EXPERIMENTS_DIR'], experiment_id)

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
    return any(filename.endswith(ext) for ext in config['IMAGE_EXTENSIONS'])


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