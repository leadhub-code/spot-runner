Spot runner
===========

[![CircleCI](https://circleci.com/gh/leadhub-code/spot-runner/tree/master.svg?style=svg&circle-token=fbc9a48dedaf93475236823b3a4ad3b6b91da208)](https://circleci.com/gh/leadhub-code/spot-runner/tree/master)

Run stuff on AWS spot instances easily.


Usage
-----

```shell
$ pip install https://github.com/leadhub-code/spot-runner/archive/master.zip
# Modify the blueprint file so it contains your KeyName and SecurityGroupIds:
$ vim examples/hello/blueprint.yaml 
$ spot-runner -v run_spot_instance --blueprint examples/hello/blueprint.yaml
```

Screenshot
----------

[![screenshot](https://s3-eu-west-1.amazonaws.com/messa-shared-files/2017/11/spot-runner-screenshot-small.png)](https://s3-eu-west-1.amazonaws.com/messa-shared-files/2017/11/spot-runner-screenshot.png)

The Blueprint file
------------------

```yaml
spot_runner_blueprint:
    region: eu-west-1
    ami_owner_id_whitelist: ['379101102735']
    task_id_template: hello-{date}-{fqdn}
    spot_price: '1.50'
    upload:
        - setup.sh
    upload_preprocessed:
        - sample_conf.yaml
    remote_command: ['bash', 'uploaded/setup.sh']
    launch_specification:
        ImageId: ami-ce76a7b7
        KeyName: your-keyname-here
        SecurityGroupIds:
          - sg-123
        InstanceType: m4.large
```
