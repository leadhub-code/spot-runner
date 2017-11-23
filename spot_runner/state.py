from contextlib import contextmanager
import logging
from pathlib import Path
import yaml


logger = logging.getLogger(__name__)


@contextmanager
def open_state_file(state_path):
    state = StateFile(state_path)
    try:
        yield state
    finally:
        state.flush()


class StateFile:

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
        return self._data.get(key, default)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
