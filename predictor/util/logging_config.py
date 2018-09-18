from cmlpcommon.config_util import get_properties_path

import json
import logging
import logging.config
import os


def setup_logging(default_path=None, default_level=logging.INFO, env_key='LOG_CFG'):
    if default_path is None:
        default_path = os.path.join(get_properties_path(), 'logging.json')
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)
