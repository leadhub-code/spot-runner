from textwrap import dedent

from spot_runner.file_transformations import \
    extract_first_line, preprocess_file, preprocess_jinja, \
    preprocess_yaml_includes


def test_extract_first_line():
    assert extract_first_line('') == ('', '')
    assert extract_first_line('\n') == ('', '')
    assert extract_first_line('a') == ('a', '')
    assert extract_first_line('a\n') == ('a', '')
    assert extract_first_line('a\n\n') == ('a', '\n')
    assert extract_first_line('a\nb') == ('a', 'b')
    assert extract_first_line('a\nb\n') == ('a', 'b\n')
    assert extract_first_line('a\nb\nc\n') == ('a', 'b\nc\n')
    assert extract_first_line('\na') == ('', 'a')


def test_preprocess_jinja():
    assert preprocess_jinja('test.txt', '') == ''
    assert preprocess_jinja('test.txt', 'foo') == 'foo'
    assert preprocess_jinja('test.txt', '{{ 1 + 2 }}') == '3'

    content = dedent('''\
        {% set x1 = 'bar' -%}
        foo {{ x1 }} {{ x2 }}
    ''')
    result = preprocess_jinja('test.txt', content, {'x2': 'baz'})
    assert result == 'foo bar baz'


def test_preprocess_jinja_with_read_file(temp_dir):
    sample_file = _write_file(temp_dir / 'sample.txt', 'bar')
    content = "foo {{ read_file('sample.txt') }} baz"
    result = preprocess_jinja(temp_dir, content, {'x2': 'baz'})
    assert result == 'foo bar baz'


def test_preprocess_yaml_includes(temp_dir):
    sample_file = _write_file(temp_dir / 'sample.txt', 'bar')
    content = dedent('''\
        foo:
            INCLUDE_TEXT: sample.txt
    ''')
    result = preprocess_yaml_includes(temp_dir, content)
    assert result == 'foo: bar\n'


def test_preprocess_file():
    assert preprocess_file('test.txt', '') == ''
    assert preprocess_file('test.txt', 'foo') == 'foo'
    assert preprocess_file('test.txt', '#!jinja\nfoo') == 'foo'
    assert preprocess_file('test.txt', '#!jinja\n{{ 1 + 2 }}') == '3'
    assert preprocess_file('test.txt', '#!yaml-includes\na: b') == 'a: b\n'


def test_preprocess_file_with_jinja_and_yaml_includes(temp_dir):
    sample_file = _write_file(temp_dir / 'sample.txt', 'bar')
    # jinja transformation first, yaml-includes second
    content = dedent('''\
        #!jinja
        #!yaml-includes
        foo:
            INCLUDE_TEXT: {{ name }}.txt
    ''')
    result = preprocess_file(temp_dir / 'test.txt', content, {'name': 'sample'})
    assert result == 'foo: bar\n'


def _write_file(path, content):
    with path.open('w') as f:
        f.write(content)
    return path
