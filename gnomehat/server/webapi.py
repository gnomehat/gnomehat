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

from gnomehat.server import datasource
from gnomehat.server.datasource import get_results, get_images, get_all_experiment_metrics, get_directory_listing, get_worker_count, get_namespaces

# TODO: Rest of world
TIMEZONE = 'US/Pacific'


@app.route('/')
def front_page():
    return flask.redirect('/default')


@app.route('/favicon.ico')
def favicon():
    return flask.send_from_directory(config['EXPERIMENTS_DIR'], 'favicon.ico')


# TODO: Surely no one will ever create a namespace named 'metrics' or 'experiment'
@app.route('/<namespace>')
def front_page_namespace(namespace):
    start_time = time.time()
    files_url = get_files_url()
    selectable_namespaces = get_namespaces(flask.request.url_root)
    for ns in selectable_namespaces:
        ns['selected'] = 'selected' if ns['name'].lower() == namespace.lower() else ''
    kwargs = {
        'results': get_results(files_url, namespace),
        'files_url': files_url,
        'worker_count': get_worker_count(),
        'server_title': datasource.get_server_title(),
        'namespaces': selectable_namespaces,
    }
    print("Generated results for front page in {:.2f} sec".format(
        time.time() - start_time))
    return flask.render_template('index.html', **kwargs)


@app.route('/metrics')
def list_metrics():
    url_root = os.path.join(flask.request.url_root, 'metrics')
    namespaces = get_namespaces(url_root)
    return flask.render_template('metrics_listing.html', namespaces=namespaces)


@app.route('/metrics/<namespace>')
def view_metrics(namespace):
    dir_name = os.path.join(config['EXPERIMENTS_DIR'], namespace)
    metrics = get_all_experiment_metrics(dir_name)
    all_keys = set(k for experiment in metrics.values() for k in experiment.keys())
    if 'notes' in all_keys:
        all_keys.remove('notes')
    all_keys = list(sorted(all_keys))
    all_keys.append('notes')

    kwargs = {
        'metrics': metrics,
        'keys': all_keys,
    }
    return flask.render_template('metrics.html', **kwargs)


@app.route('/demos')
def view_demos():
    kwargs = {
        'demos': get_demos(),
        'files_url': get_files_url(),
    }
    return flask.render_template('demos.html', **kwargs)


def get_demos():
    return [{
        'name': 'Mask_RCNN',
        'title': 'Semantic Segmentation',
        'description': 'Detect and outline people, cars, animals and more in input images.',
        'image_url': 'static/images/screenshot_Mask_RCNN.jpg',
        }, {
        'name': 'progressive_growing_of_gans',
        'title': 'Progressive Growing of Generative Adversarial Networks',
        'description': 'Generate photorealistic faces of fake celebrities',
        'image_url': 'static/images/screenshot_progressive_growing_of_gans.jpg',
        }, {
        'name': 'char_rnn',
        'title': 'Recurrent Neural Network for Text',
        'description': 'Generate Shakespeare, encyclopedia articles, and more.',
        'image_url': 'static/images/screenshot_char_rnn.jpg',
        }, {
        'name': 'variational-autoencoder',
        'title': 'Variational Autoencoder',
        'description': 'Reconstruct MNIST digits with a variational autoencoder',
        'image_url': 'static/images/screenshot_variational_autoencoder.jpg',
        }, {
        'name': 'classifier-cifar10',
        'title': 'Image Classifier',
        'description': 'Use Gnomehat to find the best parameters for training a classification network.',
        'image_url': 'static/images/screenshot_classifier_cifar10.jpg',
        },
        # TODO: open set classifier
        # TODO: Starcraft II reinforcement learning
    ]


@app.route('/demos/<demo_name>')
def run_demo(demo_name):
    assert demo_name in [demo['name'] for demo in get_demos()]

    # can't see any way this might possibly go wrong
    # todo: proper temp dir that cleans itself up
    os.chdir('/tmp')
    cmd = 'rm -rf {0}; (gnomehat demo {0}; rm -rf {0}) &'.format(demo_name)
    subprocess.run(cmd, shell=True)
    return flask.redirect('/')


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


@app.route('/stop_job', methods=['POST'])
def stop_job():
    print("Stop job: {}".format(flask.request.get_json()))
    job_id = flask.request.get_json()['id']
    filename = os.path.join(config['EXPERIMENTS_DIR'], job_id, 'worker_abort')
    with open(filename, 'w') as fp:
        fp.write('OK')
    filename = os.path.join(config['EXPERIMENTS_DIR'], job_id, 'worker_finished')
    with open(filename, 'w') as fp:
        fp.write('OK')
    return 'OK'


@app.route('/info')
def get_info():
    info = hostinfo.get_hostinfo(config['EXPERIMENTS_DIR'])
    return json.dumps(info, indent=2)


@app.route('/experiment/<experiment_namespace>/<experiment_id>')
def view_experiment(experiment_namespace, experiment_id):
    dir_path = os.path.join(config['EXPERIMENTS_DIR'], experiment_namespace, experiment_id)
    files_url = get_files_url(experiment_namespace)
    print('dir_path {}'.format(dir_path))
    image_groups = []

    for name, images in get_images(dir_path):
        url_latest_n = []
        for image in sorted(images)[-5:]:
            url = '/'.join([files_url, experiment_namespace, experiment_id, image])
            url_latest_n.append(url)

        image_groups.append({
            'name': name,
            'url_latest_5': url_latest_n,
            'url_latest': url_latest_n[-1],
        })
    image_groups.sort(key=lambda x: x['name'])

    console_port = 8765

    # When this page is viewed, spawn a Tensorboard server (if applicable)
    tensorboard_port = spawn_tensorboard(os.path.join(dir_path, 'runs'))

    kwargs = {
        'experiment_id': experiment_id,
        'experiment_namespace': experiment_namespace,
        'files_url': files_url,
        'image_groups': image_groups,
        'websocket_host': websocket_host(),
        'websocket_port': console_port,
        'tensorboard_host': tensorboard_host(),
        'tensorboard_port': tensorboard_port,
    }
    return flask.render_template('experiment.html', **kwargs)


@app.route('/experiment/<experiment_namespace>/<experiment_id>/files')
def view_experiment_listing(experiment_namespace, experiment_id):
    full_path = os.path.join(config['EXPERIMENTS_DIR'], experiment_namespace, experiment_id)
    listing = get_directory_listing(full_path)
    kwargs = {
        'listing': listing,
        'cwd': experiment_id,
        'experiment_namespace': experiment_namespace,
        'experiment_id': experiment_id,
        'files_url': get_files_url(experiment_namespace),
    }
    return flask.render_template('experiment_listing.html', **kwargs)


@app.route('/experiment/<experiment_namespace>/<experiment_id>/tensorboard')
def experiment_tensorboard(experiment_namespace, experiment_id):
    # Spawn a Tensorboard server
    tb_log_dir = os.path.join(config['EXPERIMENTS_DIR'], experiment_namespace, experiment_id, 'runs')
    tensorboard_port = spawn_tensorboard(tb_log_dir)
    tensorboard_url = 'http://{}:{}'.format(tensorboard_host(), tensorboard_port)

    # HACK: Wait for tensorboard to load. TODO preload it
    time.sleep(3)

    return flask.redirect(tensorboard_url)


@app.route('/experiment/<experiment_namespace>/<experiment_id>/visdom')
def experiment_visdom(experiment_namespace, experiment_id):
    # Spawn a Visdom server, just an empty test page for now
    # TODO: Include a default visdom.py that just prints all images
    visdom_dir = os.path.join(config['EXPERIMENTS_DIR'], experiment_namespace, experiment_id)
    visdom_host = tensorboard_host()
    visdom_port = spawn_visdom(visdom_dir)
    visdom_url = 'http://{}:{}'.format(visdom_host, visdom_port)

    # HACK: Wait for visdom to load. TODO preload it
    time.sleep(1)

    return flask.redirect(visdom_url)


def spawn_tensorboard(logdir):
    # Clean up any previous unused sockets for this experiment
    # TODO: something much much more sophisticated
    os.system('pkill -f tensorboard')

    portnum = random.randint(21000, 21999)
    # TODO proper input sanitizing and process pool and resource management and and ...
    cmd = 'CUDA_VISIBLE_DEVICES="" tensorboard --logdir {} --port {} & >/dev/null'.format(logdir, portnum)
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


def get_files_url(namespace=None):
    if namespace:
        return os.path.join(flask.request.url_root, 'experiments', namespace)
    return os.path.join(flask.request.url_root, 'experiments')


def websocket_host():
    host = flask.request.url_root.replace('http://', '').rstrip('/')
    host = host.split(':')[0]
    return host


def tensorboard_host():
    host = flask.request.url_root.replace('http://', '').rstrip('/')
    host = host.split(':')[0]
    return host
