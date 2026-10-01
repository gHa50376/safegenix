@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo D-SAFE V36.4.114 - GOOGLE DRIVE TEST
echo ============================================

python --version >nul 2>&1
if errorlevel 1 (
  echo Python tidak ditemukan. Pastikan Python sudah terpasang dan ada di PATH.
  pause
  exit /b 1
)

python -c "import streamlit, googleapiclient, google_auth_oauthlib" >nul 2>&1
if errorlevel 1 (
  echo Menyiapkan paket yang diperlukan...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Instalasi paket gagal.
    pause
    exit /b 1
  )
)

if not exist ".streamlit\secrets.toml" (
  echo.
  echo BELUM ADA .streamlit\secrets.toml
  echo Salin .streamlit\secrets.toml.example menjadi secrets.toml lalu isi Client ID, Client Secret, redirect URI dan email Admin.
  echo Untuk uji lokal gunakan redirect_uri = "http://localhost:8501/"
  echo.
  pause
  exit /b 1
)

python -m streamlit run app.py
endlocal
