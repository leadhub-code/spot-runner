import boto3
from datetime import datetime
import logging
import hashlib
from pathlib import Path
from reprlib import repr as smart_repr
from socket import getfqdn
import subprocess
from time import monotonic as monotime, sleep

from .file_transformations import preprocess_file


logger = logging.getLogger(__name__)


class RunSpotInstance:

    console_output_timeout = 180

    def __init__(self, state, blueprint, temp_dir):
        self.state = state
        self.blueprint = blueprint
        self.temp_dir = temp_dir
        self.ec2_client = boto3.client('ec2', region_name=blueprint.region_name)
        self._instance_info = None

    def run_spot_instance(self):
        self.ensure_instance()
        self.instance_info()
        self.upload()
        self.run_ssh(self.blueprint.remote_command)

    def ensure_instance(self):
        if self.state.get('instance_id'):
            logger.info('Instance id: %s', self.state['instance_id'])
        elif not self.state.get('spot_instance_request_id'):
            self.create_spot_instance_request()

    def upload(self):
        build_dir = self.prepare_upload_build()
        for p in '/bin/tar', '/usr/bin/tar':
            if Path(p).exists():
                tar_path = p
                break
        else:
            raise Exception('Could not find tar')
        data = subprocess.check_output([str(tar_path), 'c', '-C', str(build_dir), '.'])
        data_sha1 = hashlib.sha1(data).hexdigest()
        if self.state.get('uploaded_data_sha1') == data_sha1:
            logger.info('Remote data are already uploaded (sha1: %s)', data_sha1)
        else:
            self.run_ssh(['mkdir', '-p', 'uploaded'])
            self.run_ssh(['tar', 'x', '-C', 'uploaded'], input=data)
            self.state['uploaded_data_sha1'] = data_sha1
            logger.info('Uploaded remote data')

    def prepare_upload_build(self):
        from shutil import copy2, copytree
        build_dir = self.temp_dir / 'upload_build'
        logger.debug('Upload build dir: %s', build_dir)
        build_dir.mkdir()
        for p in self.blueprint.upload_paths:
            if not p.exists():
                raise Exception('Upload item does not exist: {}'.format(p))
            if p.is_dir():
                logger.info('Copying directory %s to %s', p, build_dir)
                copytree(str(p), str(build_dir / p.name))
            else:
                logger.info('Copying file %s to %s', p, build_dir)
                copy2(str(p), str(build_dir / p.name))
        for p in self.blueprint.upload_preprocessed_paths:
            if not p.is_file():
                raise Exception('Preprocess path must be file: {}'.format(p))
            content = preprocess_file(p, values={
                'instance_id': self.state['instance_id'],
                'task_id': self.state['task_id'],
            })
            target_path = build_dir / p.name
            if target_path.exists():
                logger.info('Rewriting file %s', target_path)
            with target_path.open('w') as f:
                f.write(content)
        return build_dir


    def run_ssh(self, cmd, input=None, tty=False):
        assert isinstance(cmd, list)
        ssh_args = [
            '-S', 'none',
            '-C',
            '-i', str(self.ssh_private_key_path()),
            '-l', self.blueprint.ssh_username or 'admin',
            '-o', 'UserKnownHostsFile=' + str(self.instance_host_key_path()),
        ]
        if tty:
            ssh_args.append('-t')
        full_cmd = [
            '/usr/bin/ssh',
        ] + ssh_args + [
            self.instance_public_ip(),
            'env',
            'TASK_ID=' + self.state['task_id'],
        ] + cmd
        logger.info('Running SSH %s', cmd)
        logger.debug('Full command: %s', full_cmd)
        subprocess.run(full_cmd, input=input, check=True)

    def ssh_private_key_path(self):
        if not self.blueprint.ssh_private_key:
            raise Exception('no SSH private key in blueprint')
        p = self.temp_dir / 'ssh_private_key'
        if not p.is_file():
            p.write_text(self.blueprint.ssh_private_key)
            p.chmod(0o600)
        return p

    def instance_host_key_path(self):
        p = self.temp_dir / 'instance_host_key'
        if not p.is_file():
            with p.open('w') as f:
                for key in self.instance_host_keys():
                    f.write('{ip} {key}\n'.format(
                        ip=self.instance_public_ip(),
                        key=key,
                    ))
        return p

    def instance_host_keys(self):
        if not self.state.get('instance_host_keys'):
            out = self.instance_console_output()
            self.state['instance_host_keys'] = parse_host_ssh_keys(out)
        return self.state['instance_host_keys']

    def instance_console_output(self):
        self.instance_ready()
        start_mt = monotime()
        while True:
            logger.info('Getting console output of instance %s...', self.instance_id())
            reply = self.ec2_client.get_console_output(DryRun=False, InstanceId=self.instance_id())
            logger.debug('reply: %s', smart_repr(reply))
            if 'Output' in reply:
                return reply['Output'].splitlines()
            if monotime() - start_mt > self.console_output_timeout:
                raise Exception('No console output received')
            logger.debug('No output yet, sleeping...')
            sleep(1)

    def instance_ready(self):
        if not self.state.get('instance_ok'):
            logger.info('Waiter instance_running...')
            waiter = self.ec2_client.get_waiter('instance_running')
            waiter.wait(DryRun=False, InstanceIds=[self.instance_id()])
            logger.info('Waiter instance_status_ok...')
            waiter = self.ec2_client.get_waiter('instance_status_ok')
            waiter.wait(DryRun=False, InstanceIds=[self.instance_id()])
            logger.info('Waiters done')
            self.state['instance_ok'] = True

    def instance_id(self):
        if not self.state.get('instance_id'):
            sir_id = self.state['spot_instance_request_id']
            wait_for_sir_fullfilled(self.ec2_client, sir_id)
            reply = self.ec2_client.describe_spot_instance_requests(
                DryRun=False, SpotInstanceRequestIds=[sir_id])
            sir_info, = reply['SpotInstanceRequests']
            instance_id = sir_info['InstanceId']
            logger.info('Retrieved instance id %s', instance_id)
            self.state['instance_id'] = instance_id
            if not self.state.get('tags_created'):
                self.tag_instance(instance_id, self.state['task_id'])
                self.tag_volumes(instance_id, self.state['task_id'])
                self.state['tags_created'] = True
            logger.info('Instance tags created')
        return self.state['instance_id']

    def tag_instance(self, instance_id, task_id):
        self.ec2_client.create_tags(
            DryRun=False, Resources=[instance_id],
            Tags=[
                {'Key': 'Name', 'Value': task_id},
                {'Key': 'TaskId', 'Value': task_id},
                {'Key': 'CreatedBy', 'Value': __name__},
            ])
        logger.info('Instance tags created')

    def tag_volumes(self, instance_id, task_id):
        result = self.ec2_client.describe_volumes(
            DryRun=False,
            Filters=[
                {'Name': 'attachment.instance-id', 'Values': [instance_id]},
            ])
        vol_ids = [volume['VolumeId'] for volume in result['Volumes']]
        self.ec2_client.create_tags(
            DryRun=False, Resources=vol_ids,
            Tags=[
                {'Key': 'TaskId', 'Value': task_id},
                {'Key': 'CreatedBy', 'Value': __name__},
            ])
        logger.info('Volume tags created: %s', vol_ids)

    def instance_info(self):
        if not self._instance_info:
            reply = self.ec2_client.describe_instances(DryRun=False, InstanceIds=[self.instance_id()])
            if not reply['Reservations']:
                raise Exception('Could not find instance {} - maybe it was deleted?'.format(self.instance_id()))
            reservation, = reply['Reservations']
            logger.debug('Reservation: %r', reservation)
            logger.info('Reservation id: %s', reservation['ReservationId'])
            instance, = reservation['Instances']
            assert instance['InstanceId'] == self.instance_id()
            assert instance['InstanceLifecycle'] == 'spot'
            logger.info('Instance state: %s (%r)', instance['State']['Name'], instance['State'])
            if instance['State']['Name'] not in ['running', 'pending']:
                raise Exception('Invalid instance state: {!r}'.format(instance['State']))
            logger.info(
                'Instance public IP address: %s (%s)',
                instance['PublicIpAddress'], instance['PublicDnsName'])
            self.state['instance_info'] = instance
            self._instance_info = instance
        return self._instance_info

    def instance_public_ip(self):
        return self.instance_info()['PublicIpAddress']

    def create_spot_instance_request(self):
        assert not self.state.get('task_id')
        task_id = generate_task_id(self.blueprint.task_id_template)
        ami_id = self.blueprint.launch_specification['ImageId']
        reply = self.ec2_client.describe_images(ImageIds=[ami_id])
        ami_info, = reply['Images']
        if self.blueprint.ami_owner_id_whitelist:
            if ami_info['OwnerId'] not in self.blueprint.ami_owner_id_whitelist:
                raise Exception('AMI OwnerId {!r} not present in whitelist'.format(ami_info['OwnerId']))
            else:
                logger.info('AMI OwnerId %r whitelisted', ami_info['OwnerId'])
        logger.debug('Launch spec: %r', self.blueprint.launch_specification)
        reply = self.ec2_client.request_spot_instances(
            DryRun=False,
            SpotPrice=self.blueprint.spot_price,
            InstanceCount=1,
            Type='one-time',
            LaunchSpecification=self.blueprint.launch_specification)
        sir_id = reply['SpotInstanceRequests'][0]['SpotInstanceRequestId']
        logger.info('Created spot instance request id: %s', sir_id)
        self.state['spot_instance_request_id'] = sir_id
        self.state['task_id'] = task_id
        self.state.flush()
        self.ec2_client.create_tags(
            DryRun=False, Resources=[sir_id],
            Tags=[
                {'Key': 'Name', 'Value': task_id},
                {'Key': 'TaskId', 'Value': task_id},
                {'Key': 'CreatedBy', 'Value': __name__},
            ])
        logger.info('Spot instance request tags created')


def generate_task_id(task_id_template):
    s = task_id_template
    s = s.replace('{date}', datetime.utcnow().strftime('%Y%m%dT%H%M%SZ'))
    s = s.replace('{fqdn}', getfqdn())
    return s


def wait_for_sir_fullfilled(ec2_client, sir_id):
    logger.info('Waiting for spot_instance_request_fulfilled %s...', sir_id)
    waiter = ec2_client.get_waiter('spot_instance_request_fulfilled')
    waiter.wait(DryRun=False, SpotInstanceRequestIds=[sir_id])
    logger.info('Done: spot_instance_request_fulfilled %s', sir_id)


def parse_host_ssh_keys(output):
    keys = []
    it = iter(output)
    for line in it:
        if '-----BEGIN SSH HOST KEY KEYS-----' in line:
            break
    for line in it:
        if '-----END SSH HOST KEY KEYS-----' in line:
            break
        keys.append(line)
    return keys
