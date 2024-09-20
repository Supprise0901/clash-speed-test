import sys
import schedule as schedule
import subprocess
import time
from datetime import datetime


# 运行 main.py 脚本
def run_main_script():
    try:
        # 获取当前 Python 可执行路径
        python_executable = sys.executable
        print("Running main.py...")
        subprocess.run([python_executable, "main.py"], check=True)
        print("main.py executed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running main.py: {e}")
        return False


# 运行 run.bat 脚本
# 定义运行 Git 命令的函数
def push_github():
    # 执行 Windows 下的 up.dat 文件
    subprocess.run('run_push.bat', shell=True)


def job():
    print(f'\n在{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}开始执行\n')
    if run_main_script():
        push_github()
        print('\n\n')
        print(f'在{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}执行结束')


# 定时任务：每小时运行一次
# schedule.every(2).hours.do(job)
# schedule.every(10).minutes.do(job)
# schedule.every(10).seconds.do(job)

# 轮询检测任务
# while True:
#     schedule.run_pending()  # 检查是否有需要运行的任务
#     time.sleep(1)  # 休眠1秒钟，防止占用过多 CPU 资源


def change_schedule():
    now = datetime.now()
    hour = now.hour

    if 6 <= hour < 18:
        schedule.every(2).hours.do(job)
    elif 18 <= hour < 23:
        schedule.every().hour.do(job)


# 初始设置，确保在程序启动时设置正确的调度
change_schedule()

while True:
    schedule.run_pending()
    time.sleep(1)

    # 每小时检查一次调度是否需要更改
    if datetime.now().minute == 0:
        change_schedule()
