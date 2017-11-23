from contextlib import contextmanager
import logging
from pathlib import Path
import yaml


logger = logging.getLogger(__name__)


@contextmanager
def open_state_file(state_path):
    '''
    Open state file. Currently supports only file paths.
    '''
    # In future there could also be object for managing state file on AWS S3.
    # TODO: move context API to StateFile itself.
    state = StateFile(state_path)
    try:
        yield state
    finally:
        state.flush()


class StateFile:
    '''
    Key-value collection (like dict) backed by YAML file.
    '''

    def __init__(self, path):
        self._path = Path(path)
        logger.info('Using state file %s', self._path)
        try:
            self._text = self._path.read_text()
            self._data = yaml.safe_load(self._text)['spot_runner_state']
        except FileNotFoundError:
            self._text = None
            self._data = {}

    def flush(self):
        '''
        Save all cnanges.
        '''
        new_text = yaml.safe_dump({'spot_runner_state': self._data})
        if self._text != new_text:
            try:
                current_text = self._path.read_text()
            except FileNotFoundError:
                current_text = None
            if current_text != self._text:
                raise Exception('State file has changed')
            self._path.write_text(new_text)
            self._text = new_text

    def get(self, key, default=None):
        '''
        Return the value for key if key is present, else default.
        '''
        return self._data.get(key, default)

    def __getitem__(self, key):
        '''
        Return the value for given key. Raise KeyError if key is not present.
        '''
        return self._data[key]

    def __setitem__(self, key, value):
        '''
        Set new value for given key
        '''
        self._data[key] = value
