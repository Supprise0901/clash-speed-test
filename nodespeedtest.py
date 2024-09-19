from pprint import pprint
import requests
import yaml
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.parse


def encode_url(url):
    """
        对 URL 进行编码
    """
    encoded_url = urllib.parse.quote_plus(url)

    # print(encoded_url)
    return encoded_url


def get_clash_pid():
    """
    查找 clash.exe 进程的 PID
    :return:
    """
    try:
        # 查找 clash.exe 进程
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq clash.exe'], stdout=subprocess.PIPE, text=True)
        output = result.stdout
        print(f"Clash 进程列表: {output}")

        # 解析输出，查找 PID
        for line in output.splitlines():
            if "clash.exe" in line:
                # 提取 PID，格式一般为：clash.exe          1234 Console    ...
                pid = line.split()[1]
                return pid
        return None
    except Exception as e:
        print(f"获取 clash.exe PID 时出错: {e}")
        return None


def kill_clash_process():
    """
    终止 clash.exe 进程
    :return:
    """
    pid = get_clash_pid()
    if pid:
        try:
            # 使用 taskkill 终止进程
            subprocess.run(['taskkill', '/PID', pid, '/F'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Clash 进程 {pid} 已被终止")
        except Exception as e:
            print(f"终止 clash.exe 进程时出错: {e}")
    else:
        print("未找到 clash.exe 进程")


def upload_yaml_to_clash():
    """
    上传 YAML 配置到 Clash 内核
    :return:
    """
    # 定义要执行的 Clash 命令和配置文件路径
    clash_executable = r'.\clash.exe'
    config_file = r'.\config.yaml'

    # 构建命令行参数，注意：每个部分要作为单独的字符串
    command = [clash_executable, '-f', config_file]

    try:
        # 执行命令行，启动 clash.exe 并传递配置文件
        cmd = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 等待 clash 进程完成
        # stdout, stderr = process.communicate()

        # 输出 clash 的 stdout 和 stderr
        if cmd:
            print("配置已成功推送到 Clash 内核")
    except Exception as e:
        print(f"执行 Clash 进程时出错: {e}")


def download_yaml(url):
    """
    下载 YAML 文件
    :param url:
    :return:
    """

    # 替换 cipher 配置
    def replace_cipher(data):
        if isinstance(data, dict):
            for key, value in data.items():
                if key == 'cipher' and value == 'ss':
                    data[key] = 'aes-128-gcm'
                elif isinstance(value, (dict, list)):
                    replace_cipher(value)
        elif isinstance(data, list):
            for item in data:
                replace_cipher(item)

    # 去重函数
    def remove_duplicates(data):
        if isinstance(data, dict):
            unique_data = {}
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    value = remove_duplicates(value)
                unique_data[key] = value
            return unique_data
        elif isinstance(data, list):
            seen = []
            unique_list = []
            for item in data:
                item = remove_duplicates(item)
                if item not in seen:
                    seen.append(item)
                    unique_list.append(item)
            return unique_list
        return data

    response = requests.get(url)
    try:
        if response.status_code == 200:
            # 下载节点保存到本地
            with open('config.yaml', 'w', encoding='utf-8') as f:
                f.write(response.text)
                print("YAML 文件已下载到本地: config.yaml")
            # 读取节点解析 YAML 文件
            with open('config.yaml', 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                # 替换 cipher 配置 cipher: aes-128-gcm
                replace_cipher(data)
                # 删除重复节点
                remove_duplicates(data)
            # 处理几点后写入到本地文件
            with open('config.yaml', 'w', encoding='utf-8') as file:
                yaml.dump(data, file, default_flow_style=False)
                return data
        else:
            raise Exception(f"无法下载 YAML 文件: {response.status_code}")
    except Exception as e:
        print(f"下载 YAML 文件时出错: {e}")
        return None


def test_proxy_delay(proxy_name):
    """
    测试节点的延迟
    :param proxy_name:
    :return:
    """
    try:
        url = f"{clash_api_url}/proxies/{proxy_name}/delay"
        params = {
            "timeout": 5000,  # 5秒超时
            "url": "http://www.google.com/generate_204"  # 更换为 Google 的测试 URL
        }
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                delay = response.json().get('delay', 'N/A')
                print(f"节点 {proxy_name} 的延迟为: {delay}ms")
                delay_results.append((proxy_name, int(delay)))  # 保存代理名称和延迟
            else:
                delay = 'N/A'
        except Exception as e:
            print(f"测试节点 {proxy_name} 延迟失败: {e}")
            delay = 'N/A'
        return delay
    except Exception as e:
        print(f"测试节点 {proxy_name} 延迟时出错: {e}")
        return 'N/A'


def get_proxies():
    """
    使用clash api获取 proxies name
    :return:
    """
    try:
        url = f"{clash_api_url}/proxies"
        response = requests.get(url)
        proxies = response.json()
        return proxies
    except Exception as e:
        print(f"获取 proxies 失败: {e}")
        return None


def generate_sorted_yaml(config, sorted_proxies):
    """
    生成新的 YAML 配置文件，按延迟从小到大排序
    :param config:
    :param sorted_proxies:
    :return:
    """
    try:
        # 过滤并重新排序 proxies
        proxies_dict = {proxy['name']: proxy for proxy in config['proxies']}

        # 重新生成排序后的代理列表
        sorted_proxy_list = []
        for name, delay in sorted_proxies:
            if name in proxies_dict:
                sorted_proxy_list.append(proxies_dict[name])
            else:
                print(f"警告: 代理 '{name}' 在 YAML 文件中未找到，跳过该代理节点")

        # 将排序后的 proxies 更新到配置文件中
        config['proxies'] = sorted_proxy_list

        # 将排序后的 name 写入到 proxy-group 中
        for group in config.get('proxy-groups', []):
            if 'proxies' in group:
                group['proxies'] = [proxy for proxy in group['proxies'] if proxy in dict(sorted_proxies).keys()]
                for group in config.get('proxy-groups', []):
                    if 'proxies' in group:
                        group['proxies'] = [name for name, delay in sorted_proxies]

        # 写入到新的 clash.yaml 文件
        with open('clash.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
        print("新的排序后的配置文件已生成: clash.yaml")
        # with open('F:/共享/vpn节点/Superspeed.yaml', 'w', encoding='utf-8') as f:
        #     yaml.dump(config, f, allow_unicode=True)
    except Exception as e:
        print(f"生成新的排序后的配置文件时出错: {e}")


def run_tests_in_parallel(proxies):
    """
    使用线程池并发测试所有节点的延迟
    :param proxies:
    :return:
    """
    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            # 提交所有任务
            futures = [executor.submit(test_proxy_delay, proxy_name) for proxy_name in proxies['proxies']]

            # 等待所有任务完成
            for future in as_completed(futures):
                try:
                    result = future.result()  # 获取任务结果
                except Exception as e:
                    print(f"任务发生异常: {e}")
    except Exception as e:
        print(f"并发测试节点延迟时出错: {e}")


if __name__ == '__main__':
    # 替换为你的订阅链接
    # yaml_url = 'https://mirror.ghproxy.com/https://raw.githubusercontent.com/Supprise0901/Fetch/main/Superspeed.yaml'
    # yaml_url = 'https://mirror.ghproxy.com/https://raw.githubusercontent.com/ripaojiedian/freenode/main/clash'
    # yaml_url = 'http://10.35.26.42:25500/sub?target=clash&url=https%3A%2F%2Fmirror.ghproxy.com%2Fhttps%3A%2F%2Fraw.githubusercontent.com%2Fripaojiedian%2Ffreenode%2Fmain%2Fclash%7Chttps%3A%2F%2Fmirror.ghproxy.com%2Fhttps%3A%2F%2Fraw.githubusercontent.com%2FSupprise0901%2FFetch%2Fmain%2FSuperspeed.yaml%7Chttps%3A%2F%2Fmirror.ghproxy.com%2Fraw.githubusercontent.com%2Faiboboxx%2Fv2rayfree%2Fmain%2Fv2%7Chttps%3A%2F%2Fmirror.ghproxy.com%2Fraw.githubusercontent.com%2Fmfuu%2Fv2ray%2Fmaster%2Fmerge%2Fmerge_clash.yaml%7Chttps%3A%2F%2Fmirror.ghproxy.com%2Fraw.githubusercontent.com%2Fpeasoft%2FNoMoreWalls%2Fmaster%2Flist.txt%7Chttps%3A%2F%2Fmirror.ghproxy.com%2Fraw.githubusercontent.com%2Faiboboxx%2Fv2rayfree%2Fmain%2Fv2%7C%7C%7C'
    urls = []
    with open('suburls', 'r') as f:
        for url in f:
            urls.append(url.strip())  # 去除行尾的换行符
    # 使用 '|' 将多个URL连接
    joined_urls = '|'.join(urls)
    encode_url(joined_urls)
    yaml_url = 'http://10.35.26.42:25500/sub?target=clash&url=' + encode_url(joined_urls)

    # 定义 Clash API 地址
    clash_api_url = 'http://127.0.0.1:9090'
    # 下载并解析 YAML 内容
    yaml_content = download_yaml(yaml_url)

    # 推送 YAML 到 Clash 内核
    kill_clash_process()
    time.sleep(2)
    upload_yaml_to_clash()

    # 获取所有代理节点并测试延迟
    proxies = get_proxies()
    # 存储所有节点的延迟测试结果
    delay_results = []
    # 超线程测试所有节点的延迟
    run_tests_in_parallel(proxies)
    time.sleep(2)
    # 按延迟从小到大排序
    sorted_delays = sorted(delay_results, key=lambda x: x[1])
    # 要删除的元素列表（只检查第一个元素）
    to_remove = ['🌍 国外媒体', '🔰 节点选择', '🍎 苹果服务', '🎥 NETFLIX', '🐟 漏网之鱼', '♻️ 自动选择', '🌏 国内媒体',
                 '📲 电报信息', '🚫 运营劫持', '🛑 全球拦截', '⛔️ 广告拦截', '🎯 全球直连', '🔰 节点选择', 'Ⓜ️ 微软服务',
                 'GLOBAL', 'DIRECT', 'REJECT']
    # 使用列表推导式删除指定的元素
    proxy_list = [item for item in sorted_delays if item[0] not in to_remove]
    pprint(proxy_list)
    # 生成新的配置文件
    generate_sorted_yaml(yaml_content, proxy_list)
    # 节点download测试
    subprocess.run(['python', 'nodedownloadtest.py'])
