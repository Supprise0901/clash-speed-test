import requests
import yaml
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


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


def upload_yaml_to_clash(config):
    """
    上传 YAML 配置到 Clash 内核
    :param config:
    :return:
    """
    # 定义要执行的 Clash 命令和配置文件路径
    clash_executable = r'.\clash.exe'
    config_file = r'.\config.yaml'

    # 构建命令行参数，注意：每个部分要作为单独的字符串
    command = [clash_executable, '-f', config_file]

    try:
        # 执行命令行，启动 clash.exe 并传递配置文件
        subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 等待 clash 进程完成
        # stdout, stderr = process.communicate()

        # 输出 clash 的 stdout 和 stderr
        print("配置已成功推送到 Clash 内核")
    except Exception as e:
        print(f"执行 Clash 进程时出错: {e}")


def download_yaml(url):
    """
    下载 YAML 文件
    :param url:
    :return:
    """
    response = requests.get(url)
    try:
        if response.status_code == 200:
            with open('config.yaml', 'w', encoding='utf-8') as f:
                f.write(response.text)
                print("YAML 文件已下载到本地: config.yaml")
            return yaml.safe_load(response.text)
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

        # 打印代理名称进行调试
        print("YAML 文件中的代理名称:")
        for name in proxies_dict.keys():
            print(name)

        print("从 Clash API 获取的排序后的代理名称:")
        for name, delay in sorted_proxies:
            print(name)

        # 重新生成排序后的代理列表
        sorted_proxy_list = []
        for name, delay in sorted_proxies:
            if name in proxies_dict:
                sorted_proxy_list.append(proxies_dict[name])
            else:
                print(f"警告: 代理 '{name}' 在 YAML 文件中未找到，跳过该代理节点")

        # 将排序后的 proxies 更新到配置文件中
        config['proxies'] = sorted_proxy_list

        # 写入到新的 config_sorted.yaml 文件
        with open('config_sorted.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
        print("新的排序后的配置文件已生成: config_sorted.yaml")
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
    yaml_url = 'http://10.35.26.42:25500/sub?target=clash&url=https%3A//mirror.ghproxy.com/raw.githubusercontent.com/mfuu/v2ray/master/merge/merge_clash.yaml'
    # 定义 Clash API 地址
    clash_api_url = 'http://127.0.0.1:9090'
    # 下载并解析 YAML 内容
    yaml_content = download_yaml(yaml_url)

    # 推送 YAML 到 Clash 内核
    kill_clash_process()
    time.sleep(2)
    upload_yaml_to_clash(yaml_content)

    # 获取所有代理节点并测试延迟
    proxies = get_proxies()

    delay_results = []
    # 单线程测试所有节点的延迟
    # for proxy_name in proxies['proxies']:
    #     delay = test_proxy_delay(proxy_name)
    #     if delay != 'N/A':
    #         delay_results.append((proxy_name, int(delay)))  # 保存代理名称和延迟

    # 超线程测试所有节点的延迟
    run_tests_in_parallel(proxies)
    time.sleep(2)
    # 按延迟从小到大排序
    sorted_delays = sorted(delay_results, key=lambda x: x[1])
    # 生成新的配置文件
    generate_sorted_yaml(yaml_content, sorted_delays)
