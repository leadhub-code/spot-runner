from spot_runner.blueprint import Blueprint


def test_load_example_bluperint(project_dir):
    assert Blueprint(project_dir / 'examples/hello/blueprint.yaml')
    assert Blueprint(project_dir / 'examples/hello_parametrized/blueprint.yaml')
