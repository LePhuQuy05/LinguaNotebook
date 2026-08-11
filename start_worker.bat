@echo off
rem Start the Celery worker (host, Intel Arc XPU).
rem --pool=solo is REQUIRED on Windows: celery's prefork pool fails to
rem deserialize tasks (fast_trace_task "expected 3, got 0").
cd /d "%~dp0backend"
"C:\Users\ASUS\AppData\Local\Programs\Python\Python312\python.exe" -m celery -A src.workers.celery_app worker --loglevel=info --pool=solo
