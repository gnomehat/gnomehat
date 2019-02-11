import os
import flask

template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates/')
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static/')
app = flask.Flask(__name__, template_folder=template_dir, static_folder=static_dir)
config = {}


def arg(name):
    return flask.request.values.get(name)

def run(app_config):
    config.update(app_config)
    from . import webapi
    app.run(config.get('GNOMEHAT_BIND_IP'),
            port=config.get('GNOMEHAT_PORT'),
            debug=config.get('DEBUG'))
