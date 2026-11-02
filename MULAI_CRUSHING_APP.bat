@echo off
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo [1/3] Membuat virtual environment...
  py -m venv venv
  if errorlevel 1 python -m venv venv
  if errorlevel 1 goto error
)
echo [2/3] Memeriksa dependensi...
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
echo [3/3] Menjalankan Crushing App...
"venv\Scripts\python.exe" app.py
goto end
:error
echo.
echo Gagal menyiapkan aplikasi. Pastikan Python tersedia dan internet aktif untuk instalasi paket.
pause
:end
endlocal
