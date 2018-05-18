# This file should contain all the @routes for the app
# Every HTTP endpoint should be neatly lined up right here
import shutil
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

from gnomehat import sysinfo, hostinfo
from gnomehat.server import app, config

from gnomehat.server.datasource import get_results, get_images

# TODO: Rest of world
TIMEZONE = 'US/Pacific'


@app.route('/')
def front_page():
    start_time = time.time()
    kwargs = {
        'results': get_results(),
        'files_url': get_files_url(),
    }
    print("Generated results for front page in {:.2f} sec".format(
        time.time() - start_time))
    return flask.render_template('index.html', **kwargs)


@app.route('/static/<path:path>')
def static_file(path):
    return flask.send_from_directory(app.static_folder, path)


# HACK: Here I use Flask to serve static files.
# For a proper service this would be handled by eg. nginx
@app.route('/experiments/<path:path>')
def static_experiments_file(path):
    if '../' in path:
        print('Error: bad input path {}'.format(path))
        flask.abort(400)
    full_path = os.path.join(config['EXPERIMENTS_DIR'], path)
    if os.path.isdir(full_path):
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
        return flask.render_template('listing.html',
                                     files_url=get_files_url(),
                                     listing=listing, cwd=path)
    else:
        # Serve an ordinary file
        return flask.send_from_directory(config['EXPERIMENTS_DIR'], path)


@app.route('/delete_job', methods=['POST'])
def delete_job():
    print("Delete job: {}".format(flask.request.get_json()))
    job_id = flask.request.get_json()['id']
    dir_name = os.path.join(config['EXPERIMENTS_DIR'], job_id)
    print("Delete {}".format(job_id))
    print("Removing {}".format(dir_name))
    # TODO: security lol
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
    console_port = spawn_console_websocket(os.path.join(dir_path, 'stdout.txt'))

    # When this page is viewed, spawn a Tensorboard server (if applicable)
    tensorboard_port = spawn_tensorboard(os.path.join(dir_path, 'runs'))

    kwargs = {
        'experiment_id': experiment_id,
        'image_groups': image_groups,
        'websocket_host': websocket_host(),
        'websocket_port': console_port,
        'files_url': get_files_url(),
        'tensorboard_host': tensorboard_host(),
        'tensorboard_port': tensorboard_port,
    }
    return flask.render_template('experiment.html', **kwargs)


# Tail -f the given filename in a websocket process
# Return the port number of the running websocketd
def spawn_console_websocket(filename):
    # Clean up any previous unused sockets for this experiment
    # TODO: something much much more sophisticated
    os.system('pkill -f websocketd')

    portnum = random.randint(20000, 20999)
    # TODO proper input sanitizing and process pool and resource management and and ...
    cmd = 'websocketd --port {:d} stdbuf -i0 -o0 -e0 tail -n 100 -f {} &'.format(portnum, filename)
    print("Running {}".format(cmd))
    os.system(cmd)
    return portnum


def spawn_tensorboard(logdir):
    # Clean up any previous unused sockets for this experiment
    # TODO: something much much more sophisticated
    os.system('pkill -f tensorboard')

    portnum = random.randint(21000, 21999)
    # TODO proper input sanitizing and process pool and resource management and and ...
    cmd = 'tensorboard --logdir {} --port {} & >/dev/null'.format(logdir, portnum)
    print("Running {}".format(cmd))
    os.system(cmd)
    return portnum


def get_files_url():
    return os.path.join(flask.request.url_root, 'experiments')


def default_image_url():
    return os.path.join(flask.request.url_root, '/static/images/default.png')


def websocket_host():
    host = flask.request.url_root.replace('http://', '').rstrip('/')
    host = host.split(':')[0]
    return host


def tensorboard_host():
    host = flask.request.url_root.replace('http://', '').rstrip('/')
    host = host.split(':')[0]
    return host


def timestamp_to_str(timestamp):
    timestamp = int(timestamp)
    value = datetime.datetime.fromtimestamp(timestamp)
    value.replace(tzinfo=pytz.timezone(TIMEZONE))
    return value.strftime('%Y-%m-%d %H:%M:%S')


