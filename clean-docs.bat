@echo off
echo ============================================
echo  LinguaNotebook — Clean Documents
echo ============================================
echo.
echo  1. Xoa TAT CA documents
echo  2. Xoa documents QUEUED only
echo  3. Xem danh sach documents
echo  4. Thoat
echo.
choice /c 1234 /m "Chon: "
if errorlevel 4 exit
if errorlevel 3 goto VIEW
if errorlevel 2 goto QUEUED
if errorlevel 1 goto ALL

:ALL
docker exec docker-postgres-1 psql -U linguanotebook -d linguanotebook -c "DELETE FROM content_blocks; DELETE FROM documents;"
echo Da xoa tat ca!
pause
exit

:QUEUED
docker exec docker-postgres-1 psql -U linguanotebook -d linguanotebook -c "DELETE FROM documents WHERE status = 'queued';"
echo Da xoa queued!
pause
exit

:VIEW
docker exec docker-postgres-1 psql -U linguanotebook -d linguanotebook -c "SELECT filename, status, total_pages FROM documents ORDER BY created_at DESC;"
pause
exit
