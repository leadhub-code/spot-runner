#!/usr/bin/env python3

import argparse
import boto3
from colorama import Fore, Style
import multiprocessing
from pprint import pprint
from textwrap import indent
import traceback
import yaml


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--verbose', '-v', action='count', default=0)
    args = p.parse_args()

    with multiprocessing.Pool(processes=16) as pool:
        ec2c = boto3.client('ec2', region_name='eu-central-1')
        regions = ec2c.describe_regions()['Regions']
        regions = sorted(regions, key=lambda region: region['RegionName'])
        for s in pool.map(dump_instances_in_region, regions):
            if s:
                print(s)


def dump_instances_in_region(region):
    try:
        region_name = region['RegionName']
        region_endpoint = region['Endpoint']

        ec2 = boto3.resource('ec2', region_name=region_name)
        instances = list(ec2.instances.all())
        if not instances:
            return None

        lines = []
        lines.append('Region: {S.BRIGHT}{F.CYAN}{name}{S.RESET_ALL} ({endpoint})'.format(F=Fore, S=Style, name=region_name, endpoint=region_endpoint))
        for instance in instances:
            public_ips = ', '.join(get_public_ips(instance.network_interfaces_attribute))
            lines.append(' '.join([
                'Instance:',
                instance.instance_id.ljust(20),
                Fore.GREEN + instance.instance_type.ljust(11) + Style.RESET_ALL,
                instance.launch_time.strftime('%Y-%m-%d'),
                instance.state['Name'].ljust(15),
                instance.virtualization_type,
                Style.BRIGHT +
                    (Fore.BLACK if instance.state['Name'] == 'terminated' else Fore.YELLOW) +
                    str(get_name(instance.tags) or '-').ljust(40) +
                    Style.RESET_ALL,
                Fore.MAGENTA + public_ips + Style.RESET_ALL,
            ]))

        return ''.join(line + '\n' for line in lines)
    except Exception as e:
        return traceback.format_exc()


def get_name(tags):
    if tags:
        for tag in tags:
            if tag['Key'] == 'Name':
                return tag['Value']


def get_public_ips(ifaces):
    for iface in ifaces:
        try:
            yield iface['Association']['PublicIp']
        except KeyError as e:
            continue


if __name__ == '__main__':
    main()
