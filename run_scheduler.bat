@echo off

echo 每2小时收集一次节点

REM 获取当前日期和时间
for /F "skip=1" %%A in ('wmic os get localdatetime') do (
    set datetime=%%A
    goto :afterloop
)
:afterloop

REM 提取日期和时间组件
set year=%datetime:~0,4%
set month=%datetime:~4,2%
set day=%datetime:~6,2%
set hour=%datetime:~8,2%
set minute=%datetime:~10,2%
set second=%datetime:~12,2%

REM 格式化时间戳
set start_time=%year%-%month%-%day% %hour%:%minute%:%second%

echo 开始时间: %start_time%

REM 切换到项目目录
cd /d D:\pyproject\clash-speed-test

REM 激活虚拟环境 (假设虚拟环境位于venv文件夹)
call venv\Scripts\activate

REM 执行Python脚本
python scheduler.py

REM 保持窗口打开，除非你不需要
pause
