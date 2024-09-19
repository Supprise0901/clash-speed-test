import requests
import time
import yaml
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pprint import pprint


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
    clash_executable = '.\clash.exe'
    config_file = '.\clash.yaml'

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


# 获取所有代理节点信息
def get_proxies():
    url = f"{CLASH_API_URL}/proxies"
    response = requests.get(url, headers=headers)
    return response.json()


# 切换到指定代理节点
def switch_proxy(proxy_name):
    url = f"{CLASH_API_URL}/proxies/{proxy_name}"
    data = {
        "name": proxy_name
    }
    response = requests.put(url, headers=headers, json=data)
    return response.json()


# 测试指定代理节点的下载速度（下载5秒后停止）
def test_proxy_speed(proxy_name):
    # 切换到该代理节点
    switch_result = switch_proxy(proxy_name)
    if 'error' in switch_result:
        print(f"Failed to switch to proxy {proxy_name}: {switch_result['error']}")
        return None

    # 设置代理
    proxies = {
        "http": CLASH_PROXY,
        "https": CLASH_PROXY,
    }

    # 开始下载并测量时间
    start_time = time.time()
    response = requests.get(test_url, stream=True, proxies=proxies)

    total_length = 0

    # 逐块下载，直到达到5秒钟为止
    for data in response.iter_content(chunk_size=4096):
        total_length += len(data)
        elapsed_time = time.time() - start_time
        if elapsed_time >= TEST_DURATION:
            break
    # 逐块下载，直到达到 10MB 为止
    # MAX_SIZE = 10 * 1024 * 1024  # 50MB 转换为字节
    # for data in response.iter_content(chunk_size=4096):
    #     total_length += len(data)
    #     # 检查是否已达到 10MB
    #     if total_length >= MAX_SIZE:
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
    proxies = get_proxies()
    proxy_names = proxies.get('proxies', {}).keys()

    # 多线程节点速度下载测试
    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            # 提交所有任务
            futures = [executor.submit(test_proxy_speed, proxy_name) for proxy_name in proxy_names]

            # 等待所有任务完成
            for future in as_completed(futures):
                try:
                    result = future.result()  # 获取任务结果
                except Exception as e:
                    print(f"任务发生异常: {e}")
    except Exception as e:
        print(f"并发测试节点延迟时出错: {e}")

    # 输出排序结果
    print("\n=== Test Results (sorted by speed) ===")


# 生成新的 YAML 配置文件
def generate_yaml(sorted_proxies):
    # 读取现有的 Clash 配置（假设已有初始配置文件）
    with open("clash.yaml", "r", encoding="utf-8") as f:
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


# 测试所有代理节点速度并生成新配置文件
if __name__ == "__main__":
    # Clash API 地址和授权信息
    CLASH_API_URL = "http://127.0.0.1:9090"  # Clash 的 API 地址
    SECRET = "your-secret-here"  # Clash API 的 secret，如果有的话

    # 请求头，包含授权信息
    headers = {
        "Authorization": f"Bearer {SECRET}",
        "Content-Type": "application/json"
    }

    # 测试文件 URL
    # test_url = "http://speedtest.tele2.net/10MB.zip"
    test_url = "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
    # Clash 的 HTTP 代理端口
    CLASH_PROXY = "http://127.0.0.1:7890"

    # 推送 YAML 到 Clash 内核
    kill_clash_process()
    time.sleep(2)
    upload_yaml_to_clash()
    time.sleep(2)
    # 存储所有节点的速度测试结果
    results_speed = []
    # 测试下载时间（秒）
    TEST_DURATION = 5
    # 第一步：测试所有节点的下载速度
    sorted_proxies = test_all_proxies()

    # 过滤出数值大于等于 0.2 的元素
    filtered_list = [item for item in results_speed if float(item[1]) >= 0.2]

    # 按照数值部分从大到小排序
    sorted_list = sorted(filtered_list, key=lambda x: float(x[1]), reverse=True)

    # 按下载速度从大到小排序
    # results_speed.sort(key=lambda x: x[1], reverse=True)
    # pprint(sorted_list)
    # 要删除的元素列表（只检查第一个元素）
    to_remove = ['🌍 国外媒体', '🔰 节点选择', '🍎 苹果服务', '🎥 NETFLIX', '🐟 漏网之鱼', '♻️ 自动选择', '🌏 国内媒体',
                 '📲 电报信息', '🚫 运营劫持', '🛑 全球拦截', '⛔️ 广告拦截', '🎯 全球直连', '🔰 节点选择', 'Ⓜ️ 微软服务',
                 'GLOBAL', 'DIRECT', 'REJECT']
    # 使用列表推导式删除指定的元素
    proxy_list = [item for item in sorted_list if item[0] not in to_remove]
    pprint(proxy_list)
    # 第二步：生成新的 YAML 配置文件
    generate_yaml(proxy_list)
