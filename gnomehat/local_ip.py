import re
import os
import socket
import subprocess


def parse_first_ipv4(line):
    regex = '\d*\.\d*\.\d*\.\d*'
    addrs = re.findall(regex, line)
    if len(addrs) > 0:
        return addrs[0]
    return None


def get_local_ip():
    lines = subprocess.check_output('ifconfig').decode('utf').splitlines()
    lines = [line for line in lines if 'inet addr' in line]
    addrs = [parse_first_ipv4(line) for line in lines]
    if not addrs:
        return None
    return has_prefix('10.', addrs) or has_prefix('192.', addrs) or addrs[0]


def has_prefix(prefix, addrs):
    for ip in addrs:
        if ip.startswith(prefix):
            return ip
    return None


if __name__ == '__main__':
    print(local_ip())
