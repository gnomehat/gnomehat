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

from gnomehat.server.datasource import get_results, get_images, get_all_experiment_metrics, get_directory_listing

# TODO: Rest of world
TIMEZONE = 'US/Pacific'


@app.route('/')
def front_page():
    start_time = time.time()
    kwargs = {
        'results': get_results(get_files_url()),
        'files_url': get_files_url(),
    }
    print("Generated results for front page in {:.2f} sec".format(
        time.time() - start_time))
    return flask.render_template('index.html', **kwargs)


@app.route('/metrics')
def view_metrics():
    metrics = get_all_experiment_metrics(config['EXPERIMENTS_DIR'])
    all_keys = set(k for experiment in metrics.values() for k in experiment.keys())
    all_keys.remove('notes')
    all_keys = list(sorted(all_keys))
    all_keys.append('notes')

    kwargs = {
        'metrics': metrics,
        'keys': all_keys
    }
    return flask.render_template('metrics.html', **kwargs)


@app.route('/demos')
def view_demos():
    kwargs = {
        'demos': [{
            'name': 'variational-autoencoder',
            'title': 'Variational Autoencoder',
            'description': 'Reconstruct MNIST digits with a variational autoencoder',
            'image_url': 'static/images/default.png',
            }, {
            'name': 'classifier-cifar10',
            'title': 'Image Classifier',
            'description': 'Train a convolutional network to classify CIFAR10 images',
            'image_url': 'static/images/default.png',
            },
        ],
        'files_url': get_files_url(),
    }
    return flask.render_template('demos.html', **kwargs)


@app.route('/demos/<demo_name>')
def run_demo(demo_name):
    # TODO: gnomehat-run the demo in question, redirect to its experiment
    return "TODO: Run demo {}".format(demo_name)


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
        listing = get_directory_listing(full_path)
        return flask.render_template('listing.html',
                                     files_url=get_files_url(),
                                     listing=listing, cwd=path)
    else:
        # Serve an ordinary file, defaulting to text
        TEXT_EXTENSIONS = ['txt', 'py', 'json', 'sh', 'c', 'gitignore', 'log']
        extension = path.lower().split('.')[-1]
        mimetype = 'text/plain' if extension in TEXT_EXTENSIONS else None
        return flask.send_from_directory(config['EXPERIMENTS_DIR'], path,
                                         mimetype=mimetype)


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
        'files_url': get_files_url(),
        'image_groups': image_groups,
        'websocket_host': websocket_host(),
        'websocket_port': console_port,
        'tensorboard_host': tensorboard_host(),
        'tensorboard_port': tensorboard_port,
    }
    return flask.render_template('experiment.html', **kwargs)


@app.route('/experiment/<experiment_id>/files')
def view_experiment_listing(experiment_id):
    full_path = os.path.join(config['EXPERIMENTS_DIR'], experiment_id)
    listing = get_directory_listing(full_path)
    kwargs = {
        'listing': listing,
        'cwd': experiment_id,
        'experiment_id': experiment_id,
        'files_url': get_files_url(),
    }
    return flask.render_template('experiment_listing.html', **kwargs)


@app.route('/experiment/<experiment_id>/tensorboard')
def experiment_tensorboard(experiment_id):
    # Spawn a Tensorboard server
    tb_log_dir = os.path.join(config['EXPERIMENTS_DIR'], experiment_id, 'runs')
    tensorboard_port = spawn_tensorboard(tb_log_dir)
    tensorboard_url = 'http://{}:{}'.format(tensorboard_host(), tensorboard_port)

    # HACK: Wait for tensorboard to load. TODO preload it
    time.sleep(1)

    return flask.redirect(tensorboard_url)


@app.route('/experiment/<experiment_id>/visdom')
def experiment_visdom(experiment_id):
    # Spawn a Visdom server, just an empty test page for now
    # TODO: Include a default visdom.py that just prints all images
    visdom_dir = os.path.join(config['EXPERIMENTS_DIR'], experiment_id)
    visdom_host = tensorboard_host()
    visdom_port = spawn_visdom(visdom_dir)
    visdom_url = 'http://{}:{}'.format(visdom_host, visdom_port)

    # HACK: Wait for visdom to load. TODO preload it
    time.sleep(1)

    return flask.redirect(visdom_url)


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


def spawn_visdom(experiment_dir):
    # Clean up any previous unused sockets for this experiment
    # TODO: something much much more sophisticated
    os.system('pkill -f visdom.server')

    portnum = random.randint(22000, 22999)
    # TODO proper input sanitizing and process pool and resource management and and ...
    cmd = 'python -m visdom.server -port {} & >/dev/null'.format(portnum)
    print("Running {}".format(cmd))
    os.system(cmd)

    # HACK: all these os.system() calls aren't funny any more, TODO refactor all of this
    cmd = '(sleep 3; visdomino --port {} --dir {}) &'.format(portnum, experiment_dir)
    os.system(cmd)
    return portnum


def get_files_url():
    return os.path.join(flask.request.url_root, 'experiments')



def websocket_host():
    host = flask.request.url_root.replace('http://', '').rstrip('/')
    host = host.split(':')[0]
    return host


def tensorboard_host():
    host = flask.request.url_root.replace('http://', '').rstrip('/')
    host = host.split(':')[0]
    return host
