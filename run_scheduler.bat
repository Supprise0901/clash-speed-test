@echo off

echo ÿ2Сʱ�ռ�һ�νڵ�

REM ��ȡ��ǰ���ں�ʱ��
for /F "skip=1" %%A in ('wmic os get localdatetime') do (
    set datetime=%%A
    goto :afterloop
)
:afterloop

REM ��ȡ���ں�ʱ�����
set year=%datetime:~0,4%
set month=%datetime:~4,2%
set day=%datetime:~6,2%
set hour=%datetime:~8,2%
set minute=%datetime:~10,2%
set second=%datetime:~12,2%

REM ��ʽ��ʱ���
set start_time=%year%-%month%-%day% %hour%:%minute%:%second%

echo ��ʼʱ��: %start_time%

REM �л�����ĿĿ¼
cd /d D:\pyproject\clash-speed-test

REM �������⻷�� (�������⻷��λ��venv�ļ���)
call venv\Scripts\activate

REM ִ��Python�ű�
python scheduler.py

REM ���ִ��ڴ򿪣������㲻��Ҫ
pause
