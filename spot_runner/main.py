import click
from datetime import datetime
import logging
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from .blueprint import Blueprint
from .state import open_state_file
from .workflow import RunSpotInstance


logger = logging.getLogger(__name__)


def spot_runner_main():
    try:
        cli(obj={})
    except SystemExit as e:
        raise e
    except BaseException as e:
        logger.exception('Spot runner failed: %r', e)
        sys.exit(1)


# Click docs; http://click.pocoo.org/5/


@click.group()
@click.option('--verbose', '-v', count=True)
@click.option('--log', metavar='FILE', help='path to log file')
@click.option('--state', metavar='FILE', help='path to state file')
@click.option('--new-state', '-n', is_flag=True, help='create new state file')
@click.pass_context
def cli(ctx, verbose, log, state, new_state):
    log_path = log or os.environ.get('SPOT_RUNNER_LOG')
    setup_logging(console_level=verbose, log_file=log_path)
    ctx.obj['state_path'] = state
    ctx.obj['state_new'] = new_state


@cli.command()
@click.option('--blueprint', metavar='FILE', default='blueprint.yaml')
@click.pass_context
def run_spot_instance(ctx, blueprint):
    bp = Blueprint(blueprint)
    state_path = Path(
        ctx.obj['state_path']
        or os.environ.get('SPOT_RUNNER_STATE')
        or Path(blueprint).with_name('state.yaml'))
    if ctx.obj['state_new']:
        if state_path.is_file():
            backup_suffix = '.backup-{date}'.format(
                date=datetime.utcnow().strftime('%Y%m%dT%H%M%SZ'))
            backup_path = state_path.with_name(state_path.name + backup_suffix)
            assert not backup_path.exists()
            logger.info('Renaming %s -> %s', state_path, backup_path)
            state_path.rename(backup_path)
    with open_state_file(state_path) as state:
        with TemporaryDirectory(prefix='spot_runner.') as td:
            r = RunSpotInstance(state=state, blueprint=bp, temp_dir=Path(td))
            r.run_spot_instance()


log_format = '%(asctime)s %(name)-22s %(levelname)5s: %(message)s'


def setup_logging(console_level, log_file=None):
    '''
    Log to stderr with given console level (0: warnings, 1: info, 2+: debug).
    Log to log file if path given.
    '''
    from logging import DEBUG, INFO, WARNING, Formatter
    from logging.handlers import WatchedFileHandler
    logging.getLogger().setLevel(DEBUG)

    if console_level < 2:
        # TODO: filter in a handler instead in logger
        logging.getLogger('botocore.vendored.requests.packages.urllib3.connectionpool').setLevel(WARNING)

    h = logging.StreamHandler()
    h.setFormatter(Formatter(log_format))
    if console_level == 0:
        h.setLevel(WARNING)
    elif console_level == 1:
        h.setLevel(INFO)
    else:
        h.setLevel(DEBUG)
    logging.getLogger().addHandler(h)

    if log_file:
        h = WatchedFileHandler(str(log_file))
        h.setFormatter(Formatter(log_format))
        h.setLevel(DEBUG)
        logging.getLogger().addHandler(h)
