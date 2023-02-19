import pandas as pd
import re
import socket
from concurrent.futures import ThreadPoolExecutor
from netmiko import ConnectHandler

# 定义设备信息
devices = [
    {
        'device_type': 'huawei',
        'ip': '10.10.10.101',
        'username': 'python',
        'password': '123',
        'port': 22,
    },
    {
        'device_type': 'huawei',
        'ip': '10.10.10.102',
        'username': 'python',
        'password': '123',
        'port': 22,
    },
    {
        'device_type': 'huawei',
        'ip': '10.10.10.100',
        'username': 'python',
        'password': '123',
        'port': 22,
    },
]

# 定义获取MAC地址的函数
def get_mac_address(net_connect, interface):
    output = net_connect.send_command(f'display mac-address {interface}')
    # 从输出中提取MAC地址
    mac_addresses = re.findall(r'(\w{4}-\w{4}-\w{4})', output)
    return mac_addresses

# 定义获取ARP信息的函数
def get_arp_info(net_connect, mac_address):
    output = net_connect.send_command(f'display arp | include {mac_address}')
    # 从输出中提取IP地址
    try:
        ip_address = re.search(r'(\d+\.\d+\.\d+\.\d+)', output).group(0)
    except AttributeError:
        ip_address = ''
    return ip_address

# 定义获取设备信息的函数
def get_device_info(device):
    # 连接设备
    net_connect = ConnectHandler(**device)
    net_connect.global_delay_factor = 3

    # 获取设备名称和IP地址
    output = net_connect.send_command('display current-configuration | include sysname')
    device_name = output.split()[1]
    device_ip = device['ip']

    # 获取接口信息
    output = net_connect.send_command('display interface brief')

    # 从输出中解析出状态为UP的接口名和类型
    up_interfaces = []
    for line in output.splitlines()[2:]:
        if 'up' in line.lower() and not re.match(r'^(Vlanif|NULL0|\(d\))', line):
            interface_name = line.split()[0]
            interface_type = re.search(r'([A-Za-z]+)', interface_name).group(0)
            up_interfaces.append((interface_name, interface_type))

    # 获取连接到每个接口的MAC地址和对应的IP地址
    data = {'设备名称': [], '设备IP地址': [], '接口名称': [], 'MAC地址': [], 'IP地址': []}
    for interface, interface_type in up_interfaces:
        if interface_type == 'GigabitEthernet':
            mac_addresses = get_mac_address(net_connect, interface)
            for mac_address in mac_addresses:
                ip_address = get_arp_info(net_connect, mac_address)
                # 将设备名称、设备IP地址、接口名称、MAC地址和IP地址添加到DataFrame
                data['设备名称'].append(device_name)
                data['设备IP地址'].append(device_ip)
                data['接口名称'].append(interface)
                data['MAC地址'].append(mac_address)
                data['IP地址'].append(ip_address)
        else:
            # 将设备名称、设备IP地址和接口名称添加到DataFrame
            data['设备名称'].append(device_name)
            data['设备IP地址'].append(device_ip)
            data['接口名称'].append(interface)
            data['MAC地址'].append('')
            data['IP地址'].append('')

    # 断开设备连接
    net_connect.disconnect()

    # 创建DataFrame
    df = pd.DataFrame(data)

    return df

# 将所有设备的DataFrame合并为一个DataFrame
with ThreadPoolExecutor(max_workers=3) as executor:
    # 为每个设备提交获取设备信息的函数
    futures = [executor.submit(get_device_info, device) for device in devices]

    # 创建一个空列表，用于存储每个设备的DataFrame
    dfs = []

    # 将每个设备的DataFrame添加到列表中
    for future in futures:
        df = future.result()
        dfs.append(df)

# 将所有设备的DataFrame合并为一个DataFrame
combined_df = pd.concat(dfs)

# 将DataFrame写入Excel文件
file_name = 'interface_and_mac_info.xlsx'
combined_df.to_excel(file_name, index=False)
