from spot_runner.state import open_state_file


def test_create_state_file(temp_dir):
    p = temp_dir / 'state.yaml'
    with open_state_file(p) as state:
        state['foo'] = 'bar'
    with p.open() as f:
        content = f.read()
    assert content == 'spot_runner_state: {foo: bar}\n'
    with open_state_file(p) as state:
        assert state['foo'] == 'bar'
