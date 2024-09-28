@echo off

REM 切换到映射的驱动器
cd "F:\共享\vpn节点"

REM 添加所有修改到暂存区
git add Superspeed
git add v2base.txt
git add latency

REM 获取当前日期和时间
for /F "tokens=2 delims==" %%A in ('wmic os get localdatetime /value') do set datetime=%%A

REM 提取日期和时间组件
set year=%datetime:~0,4%
set month=%datetime:~4,2%
set day=%datetime:~6,2%
set hour=%datetime:~8,2%
set minute=%datetime:~10,2%
set second=%datetime:~12,2%

REM 格式化时间戳
set TIMESTAMP=%year%-%month%-%day% %hour%:%minute%:%second%

REM 提交所有变更
git commit -m "%TIMESTAMP% Update"

:retry
REM 推送到远程仓库
git push origin main 

if %errorlevel% neq 0 (
    echo 推送失败，正在尝试合并并重试...
    git fetch origin
    git merge origin/main --allow-unrelated-histories

    if %errorlevel% neq 0 (
        echo 合并失败，自动解决冲突...
        git checkout --ours Superspeed
        git checkout --ours v2base.txt
        git checkout --ours latency
        git add Superspeed.yaml
        git add v2base.txt
        git add clash.yaml
        git commit -m "Auto-resolve merge conflict %TIMESTAMP%"
    )

    git push origin main --force
    goto :retry
)

REM 等待 5秒钟
timeout /nobreak /t 5 >nul