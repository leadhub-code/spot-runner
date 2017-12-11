import logging
from pathlib import Path
from pytest import fixture


@fixture
def temp_dir(tmpdir):
    return Path(str(tmpdir))


@fixture
def project_dir():
    here = Path(__file__).parent
    return here.parent.resolve()
