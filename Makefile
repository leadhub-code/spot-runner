python3=python3
venv_dir=local/venv

check: $(venv_dir)/packages-installed
	$(venv_dir)/bin/pytest -vs tests

venv: $(venv_dir)/packages-installed

ec2_ls: $(venv_dir)/packages-installed
	test -d $(venv_dir)/lib/*/*/colorama || $(venv_dir)/bin/pip install colorama
	$(venv_dir)/bin/python util/ec2_ls.py

$(venv_dir)/packages-installed: setup.py requirements-tests.txt
	test -d $(venv_dir) || $(python3) -m venv $(venv_dir)
	$(venv_dir)/bin/pip install -U pip wheel
	$(venv_dir)/bin/pip install -r requirements-tests.txt
	$(venv_dir)/bin/pip install -e .
	touch $@
