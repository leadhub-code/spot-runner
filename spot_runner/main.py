import click
from datetime import datetime
import logging
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from .blueprint import Blueprint
from .errors import AppError
from .state import open_state_file
from .workflow import RunSpotInstance


logger = logging.getLogger(__name__)


def spot_runner_main():
    try:
        cli(obj={})
    except SystemExit as e:
        raise e
    except AppError as e:
        logger.error('Spot runner failed: %s', e)
        sys.exit(1)
    except BaseException as e:
        # we want error messages to go into log; default handlers only prints to stderr
        logger.exception('Spot runner failed: %r', e)
        sys.exit(1)


# Click docs; http://click.pocoo.org/5/


@click.group()
@click.option('--verbose', '-v', count=True)
@click.option('--log', metavar='FILE', help='path to log file')
def cli(verbose, log):
    log_path = log or os.environ.get('SPOT_RUNNER_LOG')
    setup_logging(console_level=verbose, log_file=log_path)


@cli.command()
@click.option('--blueprint', metavar='FILE', default='blueprint.yaml')
@click.option('--state', metavar='FILE', help='path to state file')
@click.option('--new-state', '-n', is_flag=True, help='create new state file')
def run_spot_instance(blueprint, state, new_state):
    bp = Blueprint(blueprint)
    state_path = Path(
        state or
        os.environ.get('SPOT_RUNNER_STATE') or
        Path(blueprint).with_name('state.yaml'))
    if new_state:
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


@cli.command()
@click.option('--blueprint', metavar='FILE', default='blueprint.yaml')
@click.option('--state', metavar='FILE', help='path to state file')
def instance_id(blueprint, state):
    '''
    Read instance id from state file
    '''
    state_path = Path(
        state or
        os.environ.get('SPOT_RUNNER_STATE') or
        Path(blueprint).with_name('state.yaml'))
    with open_state_file(state_path) as state:
        print(state['instance_id'])


@cli.command()
@click.option('--blueprint', metavar='FILE', default='blueprint.yaml')
@click.option('--state', metavar='FILE', help='path to state file')
def ip_address(blueprint, state):
    '''
    Read instance id from state file
    '''
    state_path = Path(
        state or
        os.environ.get('SPOT_RUNNER_STATE') or
        Path(blueprint).with_name('state.yaml'))
    with open_state_file(state_path) as state:
        print(state['instance_info']['PublicIpAddress'])


@cli.command()
@click.option('--blueprint', metavar='FILE', default='blueprint.yaml')
@click.option('--state', metavar='FILE', help='path to state file')
@click.option('--user', metavar='USERNMAME', help='username to login as')
@click.argument('command', nargs=-1)
def ssh(blueprint, state, user, command):
    bp = Blueprint(blueprint)
    state_path = Path(
        state or
        os.environ.get('SPOT_RUNNER_STATE') or
        Path(blueprint).with_name('state.yaml'))
    with open_state_file(state_path) as state:
        with TemporaryDirectory(prefix='spot_runner.') as td:
            r = RunSpotInstance(state=state, blueprint=bp, temp_dir=Path(td))
            if command:
                r.run_ssh_command(user=user, command=command)
            else:
                r.run_interactive_ssh(user=user)


log_format = '%(asctime)s %(name)-22s %(levelname)5s: %(message)s'


def setup_logging(console_level, log_file=None):
    '''
    Log to stderr with given console level (0: warnings, 1: info, 2+: debug).
    Log to log file if path given.
    '''
    from logging import DEBUG, INFO, WARNING, Formatter
    from logging.handlers import WatchedFileHandler
    logging.getLogger().setLevel(DEBUG)

    if console_level < 3:
        # TODO: filter in a handler instead in logger
        logging.getLogger('botocore').setLevel(INFO)

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
