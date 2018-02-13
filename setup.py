#!/usr/bin/env python3

from setuptools import setup, find_packages


setup(
    name='spot-runner',
    version='0.0.1',
    description='AWS EC2 spot instance runner',
    url='https://github.com/leadhub-code/spot-runner',
    author='Petr Messner',
    author_email='petr.messner@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='AWS EC2 spot runner',
    packages=find_packages(exclude=['contrib', 'doc', 'tests']),
    install_requires=[
        'boto3',
        'click',
        'jinja2',
        'pyyaml',
    ],
    entry_points={
        'console_scripts': [
            'spot-runner=spot_runner:spot_runner_main',
        ],
    },
)
