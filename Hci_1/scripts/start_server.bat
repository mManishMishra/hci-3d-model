@echo off
REM HCI FastAPI server — use conda env with working PyTorch (base anaconda may fail on c10.dll)
set PYTHON=C:\Users\DELL\anaconda3\envs\improved_model_train\python.exe
if not exist "%PYTHON%" (
  echo ERROR: improved_model_train env not found at %PYTHON%
  exit /b 1
)
cd /d "%~dp0..\web"
echo Starting HCI server with %PYTHON%
"%PYTHON%" server.py
