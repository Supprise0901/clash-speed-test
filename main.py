import re
import uuid
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


def upload_yaml_to_clash(path='config.yaml'):
    """
    上传 YAML 配置到 Clash 内核
    :return:
    """
    # 定义要执行的 Clash 命令和配置文件路径
    clash_executable = r'.\clash.exe'
    # config_file = path

    # 构建命令行参数，注意：每个部分要作为单独的字符串
    command = [clash_executable, '-f', path]

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


def download_yaml():
    """
    下载 YAML 文件
    """

    def replace_cipher(data):

        for config in data.get('proxies', []):
            if config.get('type') == 'ss':
                config['cipher'] = 'aes-128-gcm'

        data['proxies'] = [proxy for proxy in data.get('proxies', []) if proxy.get('network') != 'grpc'
                           and proxy.get('network') != 'h2']

        return data

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

    def fix_yaml_errors(yaml_content):
        yaml_content = re.sub(r'!<str>\s*', '', yaml_content)
        return yaml_content

    def is_valid_uuid(uuid_to_test, version=4):
        uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
                                re.IGNORECASE)
        if not uuid_regex.match(uuid_to_test):
            return False
        try:
            uuid_obj = uuid.UUID(uuid_to_test, version=version)
        except ValueError:
            return False
        return str(uuid_obj) == uuid_to_test

    def clear_invalid_uuid(data):
        valid_proxies = []
        for proxy in data.get('proxies', []):
            uuid = proxy.get('uuid')
            if uuid is None:
                # print(f"代理没有 UUID，代理名称: {proxy.get('name')}")
                continue
            if is_valid_uuid(uuid):
                valid_proxies.append(proxy)
            # else:
            #     print(f"无效 UUID: {uuid}，代理名称: {proxy.get('name')}")
        data['proxies'] = valid_proxies
        return data

    def checkbox_config(data):
        # 获取现有的代理名称列表
        proxy_list = data.get("proxies", [])
        proxies_name = []
        for proxy in proxy_list:
            if 'name' in proxy:
                proxies_name.append(proxy['name'])
        # 将排序后的 name 写入到 proxy-group 中
        for group in data.get('proxy-groups', []):
            if 'proxies' in group:
                if 'proxies' in group:
                    group['proxies'] = [name for name in proxies_name]
        return data

    try:
        with open('suburls', 'r') as f:
            urls = [url.strip() for url in f if url.strip()]  # 去除行尾的换行符
            valid_urls = []
            for url in urls:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    valid_urls.append(url)
                else:
                    print(f"无效 {url} 失败: {response.status_code}")

        joined_urls = '|'.join(valid_urls)
        # 本地下载
        yaml_url = f'http://127.0.0.1:25500/sub?target=clash&emoji=false&url={joined_urls}'
        # 容器下载
        # yaml_url = f'http://10.35.26.42:25500/sub?target=clash&emoji=false&url={joined_urls}'
        response = requests.get(yaml_url)

        if response.status_code == 200:
            with open('config.yaml', 'w', encoding='utf-8') as f:
                f.write(response.text)
                print("YAML 文件已下载到本地: config.yaml")

            with open('config.yaml', 'r', encoding='utf-8') as file:
                yaml_content = fix_yaml_errors(file.read())
                data = yaml.safe_load(yaml_content)
                data = replace_cipher(data)
                data = remove_duplicates(data)
                data = clear_invalid_uuid(data)
                # to_remove 是全局变量，传入 checkbox_config
                data = checkbox_config(data)
                with open('config.yaml', 'w', encoding='utf-8') as file:
                    yaml.dump(data, file, default_flow_style=False, allow_unicode=True)
                    print("YAML 修正后保存: config.yaml")
                    # return data
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
            "url": "https://www.google.com"  # 更换为 Google 的测试 URL
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

        # 写入到新的 latency 文件
        with open('latency', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
        print("新的排序后的配置文件已生成: latency")

    except Exception as e:
        print(f"生成新的排序后的配置文件时出错: {e}")


def run_tests_in_parallel():
    """
    使用线程池并发测试所有节点的延迟

    """
    # 获取所有代理节点并测试延迟
    proxies = get_proxies()
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


def start_latency_testing():
    # 下载并解析 YAML 内容
    yaml_content = download_yaml()
    # 推送 YAML 到 Clash 内核
    kill_clash_process()
    time.sleep(2)
    upload_yaml_to_clash()
    # 超线程测试所有节点的延迟
    run_tests_in_parallel()
    time.sleep(2)
    # 按延迟从小到大排序
    sorted_delays = sorted(delay_results, key=lambda x: x[1])
    # 使用列表推导式删除指定的元素
    proxy_list = [item for item in sorted_delays if item[0] not in to_remove]
    pprint(proxy_list)
    print(f'收集延迟有效节点{len(proxy_list)}个')
    # 生成新的配置文件
    generate_sorted_yaml(yaml_content, proxy_list)


# 切换到指定代理节点
def switch_proxy(proxy_name):
    """
    切换 Clash 中策略组的代理节点。
    :param proxy_name: 要切换到的代理节点名称
    :return: 返回切换结果或错误信息
    """
    url = f"{clash_api_url}/proxies/%F0%9F%8E%AF%20%E5%85%A8%E7%90%83%E7%9B%B4%E8%BF%9E"
    data = {
        "name": proxy_name
    }

    try:
        response = requests.put(url, json=data)
        # 检查响应状态
        if response.status_code == 204:  # Clash API 切换成功返回 204 No Content
            print(f"\nSwitched to proxy '{proxy_name}' in selector '🎯%20全球直连' successfully.")
            return {"status": "success", "message": f"Switched to proxy '{proxy_name}'."}
        else:
            # print(f"Failed to switch proxy. HTTP status code: {response.status_code}")
            return response.json()
    except Exception as e:
        print(f"Error occurred: {e}")
        return {"status": "error", "message": str(e)}


# 测试指定代理节点的下载速度（下载5秒后停止）
def test_proxy_speed(proxy_name):
    # 切换到该代理节点
    switch_proxy(proxy_name)
    # 等待代理切换生效
    time.sleep(1)

    # 设置代理
    proxies = {
        "http": 'http://127.0.0.1:7890',
        "https": 'http://127.0.0.1:7890',
    }

    # 开始下载并测量时间
    start_time = time.time()
    # response = requests.get(test_url, stream=True, proxies=proxies, timeout=test_duration)
    # 计算总下载量
    total_length = 0
    # 测试下载时间（秒）
    test_duration = 5  # 逐块下载，直到达到5秒钟为止
    # for data in response.iter_content(chunk_size=4096):
    #     total_length += len(data)
    #     elapsed_time = time.time() - start_time
    #     if elapsed_time >= test_duration:
    #         break

    # 不断发起请求直到达到时间限制
    while time.time() - start_time < test_duration:
        try:
            response = requests.get(test_url, stream=True, proxies=proxies, headers={'Cache-Control': 'no-cache'},
                                    timeout=test_duration)
            for data in response.iter_content(chunk_size=524288):
                total_length += len(data)
                if time.time() - start_time >= test_duration:
                    break
            # time.sleep(0.5)  # 引入短暂的延迟，防止过快完成
        except Exception as e:
            print(f"测试节点 {proxy_name} 下载失败: {e}")

    # 逐块下载，直到达到 10MB 为止
    # max_size = 10 * 1024 * 1024  # 50MB 转换为字节
    # for data in response.iter_content(chunk_size=4096):
    #     total_length += len(data)
    #     # 检查是否已达到 10MB
    #     if total_length >= max_size:
    #         break

    # 计算速度：Bps -> MB/s
    elapsed_time = time.time() - start_time
    speed = total_length / elapsed_time if elapsed_time > 0 else 0

    # 返回下载速度（MB/s）
    print(f"\nTesting proxy: {proxy_name}")
    print(f"Total downloaded: {total_length} bytes in {elapsed_time:.2f} seconds.")
    print(f"Average speed: {speed / 1024 / 1024:.2f} MB/s")

    results_speed.append((proxy_name, f"{speed / 1024 / 1024:.2f}"))  # 记录速度测试结果
    return speed / 1024 / 1024  # 返回 MB/s


# 测试所有代理节点的下载速度，并排序结果
def test_all_proxies():
    try:
        proxies = get_proxies()
        proxy_names = proxies.get('proxies', {}).keys()

        # 单线程节点速度下载测试
        for proxy_name in proxy_names:
            if proxy_name not in to_remove:
                test_proxy_speed(proxy_name)

        # 多线程节点速度下载测试
        # with ThreadPoolExecutor(max_workers=1) as executor:
        #     # 提交所有任务
        #     futures = [executor.submit(test_proxy_speed, proxy_name) for proxy_name in proxy_names]
        #
        #     # 等待所有任务完成
        #     for future in as_completed(futures):
        #         try:
        #             result = future.result()  # 获取任务结果
        #         except Exception as e:
        #             print(f"任务发生异常: proxy timed out")

        # 输出排序结果
        print("\n=== Test Results (sorted by speed) ===")
    except Exception as e:
        print(f"测试节点速度时出错: {e}")


# 生成新的 YAML 配置文件
def generate_yaml(sorted_proxies):
    # 读取现有的 Clash 配置（假设已有初始配置文件）
    with open("latency", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 获取现有的代理列表
    proxy_list = config.get("proxies", [])

    # 按测试结果重新排序代理
    new_proxy_list = []
    for proxy_name, _ in sorted_proxies:
        for proxy in proxy_list:
            if proxy.get("name") == proxy_name:
                new_proxy_list.append(proxy)
                break

    # 更新配置中的代理列表
    config["proxies"] = new_proxy_list

    # 将排序后的 name 写入到 proxy-group 中
    for group in config.get('proxy-groups', []):
        if 'proxies' in group:
            group['proxies'] = [proxy for proxy in group['proxies'] if proxy in dict(sorted_proxies).keys()]
            for group in config.get('proxy-groups', []):
                if 'proxies' in group:
                    group['proxies'] = [name for name, delay in sorted_proxies]

    # 将新配置写入到新的 YAML 文件
    with open("Superspeed.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True)

    print(f"New YAML configuration saved to Superspeed.yaml")


#
def start_download_test(speed_limit):
    """
    开始下载测试

    """
    # 推送 YAML 到 Clash 内核
    kill_clash_process()
    time.sleep(2)
    upload_yaml_to_clash(path='latency')
    time.sleep(2)

    # 第一步：测试所有节点的下载速度
    test_all_proxies()

    # 过滤出速度大于等于 speed_limit 的节点
    filtered_list = [item for item in results_speed if float(item[1]) >= float(f'{speed_limit}')]

    # 按下载速度从大到小排序
    sorted_list = sorted(filtered_list, key=lambda x: float(x[1]), reverse=True)

    # 使用列表推导式删除指定的元素
    proxy_list = [item for item in sorted_list if item[0] not in to_remove]
    pprint(proxy_list)

    # 读取延迟 latency文件
    with open("latency", "r", encoding='utf-8') as file:
        data = yaml.safe_load(file)

    # 获取所有节点数量
    node_count = len(data.get('proxies', []))
    print(f'\n收集延迟有效节点{node_count}个')
    print(f'收集下载有效节点{len(proxy_list)}个')
    # 第二步：生成新的 YAML 配置文件
    generate_yaml(proxy_list)


if __name__ == '__main__':
    print('YAML 文件开始下载。。。。。')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
    # 要删除的元素列表（只检查第一个元素）
    to_remove = ['🌍 国外媒体', '🔰 节点选择', '🍎 苹果服务', '🎥 NETFLIX', '🐟 漏网之鱼', '♻️ 自动选择', '🌏 国内媒体',
                 '📲 电报信息', '🚫 运营劫持', '🛑 全球拦截', '⛔️ 广告拦截', '🎯 全球直连', '🔰 节点选择', 'Ⓜ️ 微软服务',
                 'GLOBAL', 'DIRECT', 'REJECT']
    # 定义 Clash API 地址
    clash_api_url = 'http://127.0.0.1:9090'
    # 存储所有节点的延迟测试结果
    delay_results = []
    # 开始延迟测试
    start_latency_testing()
    # 节点延迟测试等待5秒钟以便 Clash 内核启动下载测试
    time.sleep(5)
    # 测试文件 URL
    # test_url = "http://speedtest.tele2.net/10MB.zip"
    test_url = "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
    # 存储所有节点的速度测试结果
    results_speed = []
    # 下载速度限制 单位 MB/s
    speed_limit = 0.1
    # 开始下载测试
    start_download_test(speed_limit)
    kill_clash_process()
