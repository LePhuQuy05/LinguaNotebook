@echo off
echo ============================================
echo  LinguaNotebook — Clean Documents
echo ============================================
echo.
echo  1. Xoa TAT CA documents + Redis queue
echo  2. Xoa documents QUEUED only + Redis queue
echo  3. Xem danh sach documents
echo  4. Thoat
echo.
choice /c 1234 /m "Chon: "
if errorlevel 4 exit
if errorlevel 3 goto VIEW
if errorlevel 2 goto QUEUED
if errorlevel 1 goto ALL

:ALL
echo Dang xoa tat ca documents...
docker exec docker-postgres-1 psql -U linguanotebook -d linguanotebook -c "DELETE FROM content_blocks; DELETE FROM documents;"
echo Dang don Redis queue...
docker exec docker-redis-1 redis-cli EVAL "local keys = redis.call('keys', 'parse:progress:*') for i=1,#keys do redis.call('del', keys[i]) end local keys2 = redis.call('keys', 'parse:cancel:*') for i=1,#keys2 do redis.call('del', keys2[i]) end return redis.call('del', 'celery', 'unacked', 'unacked_index')" 0 >nul 2>&1
docker exec docker-redis-1 redis-cli EVAL "local keys = redis.call('keys', 'celery-task-meta-*') for i=1,#keys do redis.call('del', keys[i]) end return #keys" 0 >nul 2>&1
echo Da xoa tat ca!
pause
exit

:QUEUED
echo Dang tim queued documents...
for /f "usebackq delims=" %%i in (`docker exec docker-postgres-1 psql -U linguanotebook -d linguanotebook -t -A -c "SELECT id FROM documents WHERE status = 'queued';"`) do (
    echo Dang purge: %%i
    docker exec docker-redis-1 redis-cli DEL "parse:progress:%%i" "parse:cancel:%%i" >nul 2>&1
)
echo Dang xoa queued documents...
docker exec docker-postgres-1 psql -U linguanotebook -d linguanotebook -c "DELETE FROM documents WHERE status = 'queued';"
echo Dang don Celery queue...
docker exec docker-redis-1 redis-cli DEL celery unacked unacked_index >nul 2>&1
echo Da xoa queued!
pause
exit

:VIEW
docker exec docker-postgres-1 psql -U linguanotebook -d linguanotebook -c "SELECT filename, status, total_pages FROM documents ORDER BY created_at DESC;"
pause
exit
