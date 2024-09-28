@echo off

REM �л���ӳ���������
cd "F:\����\vpn�ڵ�"

REM ��������޸ĵ��ݴ���
git add Superspeed
git add v2base.txt
git add latency

REM ��ȡ��ǰ���ں�ʱ��
for /F "tokens=2 delims==" %%A in ('wmic os get localdatetime /value') do set datetime=%%A

REM ��ȡ���ں�ʱ�����
set year=%datetime:~0,4%
set month=%datetime:~4,2%
set day=%datetime:~6,2%
set hour=%datetime:~8,2%
set minute=%datetime:~10,2%
set second=%datetime:~12,2%

REM ��ʽ��ʱ���
set TIMESTAMP=%year%-%month%-%day% %hour%:%minute%:%second%

REM �ύ���б��
git commit -m "%TIMESTAMP% Update"

:retry
REM ���͵�Զ�ֿ̲�
git push origin main 

if %errorlevel% neq 0 (
    echo ����ʧ�ܣ����ڳ��Ժϲ�������...
    git fetch origin
    git merge origin/main --allow-unrelated-histories

    if %errorlevel% neq 0 (
        echo �ϲ�ʧ�ܣ��Զ������ͻ...
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

REM �ȴ� 5����
timeout /nobreak /t 5 >nul