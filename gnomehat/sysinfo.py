import os
from subprocess import check_output

def nv_id_to_name(device_id):
    return {
            '13c0':    'GM204 [GeForce GTX 980]',
            '13c2':    'GM204 [GeForce GTX 970]',
            '1401':    'GM206 [GeForce GTX 960]',
            '1407':    'GM206 [GeForce GTX 750 v2]',
            '15f7':    'GP100 [Tesla P100 PCIe 12GB]',
            '15f8':    'GP100 [Tesla P100 PCIe 16GB]',
            '15f9':    'GP100 [Tesla P100 SMX2 16GB]',
            '1b00':    'GP102 [GeForce TITAN X]',
            '1b06':    'GP102 [GeForce GTX 1080 Ti]',
            '1b30':    'GP102 [Quadro P6000]',
            '1b38':    'GP102 [Tesla P40]',
            '1b80':    'GP104 [GeForce GTX 1080]',
            '1b81':    'GP104 [GeForce GTX 1070]',
            '1b84':    'GP104 [GeForce GTX 1060 3GB]',
            '1ba0':    'GP104 [GeForce GTX 1080 Mobile]',
            '1ba1':    'GP104 [GeForce GTX 1070 Mobile]',
            '1bb0':    'GP104 [Quadro P5000]',
            '1bb3':    'GP104 [Tesla P4]',
            '1bb6':    'GP104 [Quadro P5000 Mobile]',
            '1bb7':    'GP104 [Quadro P4000 Mobile]',
            '1bb8':    'GP104 [Quadro P3000 Mobile]',
            '1be0':    'GP104 [GeForce GTX 1080 Mobile]',
            '1be1':    'GP104 [GeForce GTX 1070 Mobile]',
            '1c02':    'GP106 [GeForce GTX 1060 3GB]',
            '1c03':    'GP106 [GeForce GTX 1060 6GB]',
            '1c20':    'GP106 [GeForce GTX 1060 Mobile]',
            '1c60':    'GP106 [GeForce GTX 1060 Mobile]',
            '1c61':    'GP106 [GeForce GTX 1050 Ti Mobile]',
            '1c62':    'GP106 [GeForce GTX 1050 Mobile]',
            '1c81':    'GP107 [GeForce GTX 1050]',
            '1c82':    'GP107 [GeForce GTX 1050 Ti]',
            '1c8c':    'GP107 [GeForce GTX 1050 Ti Mobile]',
            '1c8d':    'GP107 [GeForce GTX 1050 Mobile]',
            '1d01':    'GP108 [GeForce GT 1030]',
            '1d10':    'GP108 [GeForce MX150]',
            '1db8':    'GV100 [Tesla V100-SXM3]',
    }.get(device_id, 'NVIDIA {}'.format(device_id))


def run(x):
    try:
        output_bytes = check_output(x, shell=True)
        return output_bytes.decode('utf-8').replace('\t', ' ').strip('\n')
    except:
        return "<error>"


def get_cpu_info():
    cpu_info = run('cat /proc/cpuinfo | grep "model name" | uniq')
    cpu_info = cpu_info.split(':')[-1].strip()
    return cpu_info


def get_ram_info():
    ram_lines = run('sudo dmidecode  -t memory | egrep "[^ ](Size|Speed)." | grep -v Unknown | grep -v "No Module Installed" | paste - - -d\;')
    ram_info = []
    for line in ram_lines.splitlines():
        if ';' in line:
            size, speed = line.split(';')
            speed = speed.split()[-2]
            size = size.split()[-2]
            ram_info.append({'speed_mhz': speed, 'size_mb': size})
    return ram_info


def get_mb_info():
    mb_info = run('sudo dmidecode -t 2 | grep "Product Name"')
    mb_info = mb_info.split('Product Name: ')[-1]
    return mb_info


def get_gpu_info():
    nv_lines = run('lspci -vv | grep "controller: NVIDIA"')
    gpu_info = []
    for line in nv_lines.splitlines():
        device_id = line.split()[7]
        gpu_info.append({
            'device_id': device_id,
            'name': nv_id_to_name(device_id)})
    return gpu_info


def get_ubuntu_version():
    ubuntu_version = run('lsb_release -a 2>/dev/null | grep Release | grep -o [0-9].*')
    return ubuntu_version


def get_all_info():
    info = {
        'cpu': get_cpu_info(),
        'ram': get_ram_info(),
        'motherboard': get_mb_info(),
        'gpu': get_gpu_info(),
        'ubuntu_version': get_ubuntu_version(),
    }
    return info
