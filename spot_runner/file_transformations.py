import logging
import jinja2
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


def preprocess_file(file_path, content=None, values=None):
    logger.info('Preprocessing %s', file_path)
    if content is None:
        with file_path.open() as f:
            content = f.read()
    base_path = Path(file_path).parent
    while True:
        first_line, rest = extract_first_line(content)
        if first_line == '#!jinja':
            logger.info('jinja transformation')
            content = preprocess_jinja(base_path, rest, values)
        elif first_line == '#!yaml-includes':
            logger.info('yaml-includes transformation')
            content = preprocess_yaml_includes(base_path, rest)
        else:
            break
    return content


def extract_first_line(content):
    parts = content.split('\n', 1)
    return (parts[0], '') if len(parts) == 1 else (parts[0].rstrip(), parts[1])


def preprocess_jinja(base_path, content, values=None):
    assert isinstance(content, str)
    values = dict(values or {})
    t = jinja2.Template(content)
    # TODO: jinja includes

    def read_file(path):
        with (base_path / path).open('r') as f:
            return f.read()

    values.update({
        'read_file': read_file,
    })
    return t.render(**values)


def preprocess_yaml_includes(base_path, content):
    assert isinstance(content, str)

    def r(obj):
        if isinstance(obj, list):
            return [r(v) for v in obj]
        if isinstance(obj, dict):
            if len(obj) == 1:
                (k, v), = obj.items()
                if k == 'INCLUDE_TEXT':
                    inc_path = base_path / v
                    logger.info('Including text file %s', inc_path)
                    with inc_path.open() as f:
                        return f.read()
                elif k == 'INCLUDE_YAML':
                    inc_path = base_path / v
                    logger.info('Including YAML file %s', inc_path)
                    with inc_path.open() as f:
                        return yaml_load(f.read())
            return {k: r(v) for k, v in obj.items()}
        return obj

    data = yaml_load(content)
    data = r(data)
    return yaml_dump(data)


def yaml_load(content):
    return yaml.safe_load(content)


def yaml_dump(obj):
    return yaml.dump(obj, width=120, default_flow_style=False, Dumper=_CustomDumper)


class _CustomDumper (yaml.SafeDumper):
    pass

def _str_representer(dumper, data):
    style = '|' if '\n' in data else None
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style=style)

_CustomDumper.add_representer(str, _str_representer)
