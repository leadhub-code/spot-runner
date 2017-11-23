import logging
from pathlib import Path
import yaml


logger = logging.getLogger(__name__)


class Blueprint:

    def __init__(self, path):
        self._path = Path(path)
        logger.info('Loading blueprint from %s', self._path)
        d = yaml.safe_load(self._path.read_text())['spot_runner_blueprint']
        base_dir = self._path.parent
        self.region_name = d['region']
        self.ami_owner_id_whitelist = d.get('ami_owner_id_whitelist') or []
        self.task_id_template = d['task_id_template']
        self.spot_price = d['spot_price']
        self.upload_paths = to_paths(base_dir, d.get('upload'))
        self.upload_preprocessed_paths = to_paths(base_dir, d.get('upload_preprocessed'))
        self.remote_command = d['remote_command']
        self.launch_specification = d['launch_specification']
        self.ssh_username = d.get('ssh_username')
        if d.get('ssh_private_key_path'):
            ssh_pk_path = base_dir / d['ssh_private_key_path']
            self.ssh_private_key = ssh_pk_path.read_text()
        else:
            self.ssh_private_key = find_ssh_key(base_dir, self.launch_specification['KeyName'])


def to_paths(base_dir, value):
    if not value:
        return []
    assert isinstance(value, list)
    return [base_dir / p for p in value]


def find_ssh_key(base_dir, key_name):
    search_paths = [
        base_dir / '{}.pem'.format(key_name),
        base_dir / 'ssh_keys/{}.pem'.format(key_name),
        Path.home() / '.ssh/{}.pem'.format(key_name),
    ]
    for p in search_paths:
        if p.is_file():
            logger.info('Reading SSH key from %s', p)
            return p.read_text()
