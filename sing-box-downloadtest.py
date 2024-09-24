import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pprint import pprint

import requests
import time


def get_singbox_node_tags(config_file):
    try:
        with open(config_file, 'r', encoding='utf-8') as file:
            config = json.load(file)

        # 获取所有的 outbounds 节点
        outbounds = config.get('outbounds', [])

        # 提取所有节点的 tag
        node_tags = [outbound.get('tag', 'Unknown') for outbound in outbounds]

        return node_tags
    except Exception as e:
        print(f"Error occurred while reading config: {e}")
        return []


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


def run_tests_in_parallel():
    """
    使用线程池并发测试所有节点的延迟

    """
    # 获取所有代理节点并测试延迟
    proxies = get_singbox_node_tags("config.json")
    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            # 提交所有任务
            futures = [executor.submit(test_proxy_delay, proxy_name) for proxy_name in proxies]

            # 等待所有任务完成
            for future in as_completed(futures):
                try:
                    result = future.result()  # 获取任务结果
                except Exception as e:
                    print(f"任务发生异常: {e}")

    except Exception as e:
        print(f"并发测试节点延迟时出错: {e}")


# 切换到指定代理节点
def switch_proxy(proxy_name):
    url = f"{clash_api_url}/proxies/{proxy_name}"
    data = {
        "name": proxy_name
    }
    response = requests.put(url, json=data)
    return response.json()


def test_download_speed(proxy_name):
    # 切换到该代理节点
    switch_result = switch_proxy(proxy_name)
    if 'error' in switch_result:
        print(f"Failed to switch to proxy {proxy_name}: {switch_result['error']}")
        return None

    proxies = {
        "http": "http://127.0.0.1:2080",
        "https": "http://127.0.0.1:2080",
    }

    try:
        # 记录开始时间
        start_time = time.time()
        # response = requests.get(test_url, stream=True, proxies=proxies, timeout=10)
        total_downloaded = 0
        # 不断发起请求直到达到时间限制
        while time.time() - start_time < test_duration:
            response = requests.get(test_url, stream=True, proxies=proxies)
            for data in response.iter_content(chunk_size=524288):
                total_downloaded += len(data)
                if time.time() - start_time >= test_duration:
                    break
            time.sleep(0.5)  # 引入短暂的延迟，防止过快完成

        # 计算下载速度 (bytes per second)
        elapsed_time = time.time() - start_time
        download_speed_bps = total_downloaded / elapsed_time
        download_speed_mbps = download_speed_bps / 1024 / 1024  # 转换为 MB/s

        # 输出结果
        print(f"\nTesting proxy: {proxy_name}")
        print(f"Total downloaded: {total_downloaded / 1024 / 1024:.2f} MB in {elapsed_time:.2f} seconds.")
        print(f"Average download speed: {download_speed_mbps:.2f} MB/s")
        results_speed.append((proxy_name, f"{download_speed_mbps:.2f}"))  # 记录速度测试结果
        return download_speed_mbps

    except requests.RequestException as e:
        print(f"Error occurred during the test: {e}")
        return None


def test_all_proxies(proxies):
    # proxies = get_singbox_node_tags("config.json")

    # 多线程节点速度下载测试
    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            # 提交所有任务
            futures = [executor.submit(test_download_speed, proxy_name) for proxy_name in proxies]

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


if __name__ == "__main__":
    clash_api_url = "http://127.0.0.1:9090"  # 请修改为你实际的 Clash API 地址
    # 设置测试文件的URL
    test_url = "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"  # 可替换为你想要测试的文件
    proxy_address = "127.0.0.1:2080"  # 代理地址
    test_duration = 5  # 测试时长（秒）
    # 要删除的元素列表（只检查第一个元素）
    to_remove = ['🌍 国外媒体', '🔰 节点选择', '🍎 苹果服务', '🎥 NETFLIX', '🐟 漏网之鱼', '♻️ 自动选择', '🌏 国内媒体',
                 '📲 电报信息', '🚫 运营劫持', '🛑 全球拦截', '⛔️ 广告拦截', '🎯 全球直连', '🔰 节点选择', 'Ⓜ️ 微软服务',
                 'GLOBAL', 'DIRECT', 'REJECT', '🍃 应用净化', '📢 谷歌FCM', '🚀 节点选择', 'dns-out']
    # 记录延迟测试结果
    delay_results = []
    # 超线程测试所有节点的延迟
    run_tests_in_parallel()
    # 按延迟从小到大排序
    sorted_delays = sorted(delay_results, key=lambda x: x[1])
    # 使用列表推导式删除指定的元素
    proxy_list = [item for item in sorted_delays if item[0] not in to_remove]
    pprint(proxy_list)
    print(f'收集下载有效节点{len(proxy_list)}个')

    # 记录下载速度测试结果
    results_speed = []
    # 开始测试
    proxy_name = [name for name, speed in proxy_list]
    test_all_proxies(proxy_name)
    # 输出结果
    # 过滤出数值大于等于 0.0 的元素
    filtered_list = [item for item in results_speed if float(item[1]) >= 0.0]
    # 按下载速度从大到小排序
    sorted_list = sorted(filtered_list, key=lambda x: float(x[1]), reverse=True)
    # 使用列表推导式删除指定的元素
    proxy_list = [item for item in sorted_list if item[0] not in to_remove]
    pprint(proxy_list)
    print(f"\nTotal proxies tested: {len(proxy_list)}")
