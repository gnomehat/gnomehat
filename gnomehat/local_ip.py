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
    fib_trie = open('/proc/net/fib_trie').read()
    addrs = re.findall('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', fib_trie)
    addrs = sorted(list(set(addrs)))
    addrs = [ip for ip in addrs if not ip.startswith('127.') and not ip.endswith('.0')
        and not ip.endswith('.255')]
    if not addrs:
        raise ValueError('No IPv4 address available')
    ten_addrs = [ip for ip in addrs if ip.startswith('10.')]
    if ten_addrs:
        return ten_addrs[-1]
    return addrs[-1]


def has_prefix(prefix, addrs):
    for ip in addrs:
        if ip.startswith(prefix):
            return ip
    return None


if __name__ == '__main__':
    print(local_ip())
