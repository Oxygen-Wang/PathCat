@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "APP=%~dp0QuietPet.py"
set "RUNNER="

REM Pick a working Python that can import tkinter, so a missing/empty
REM Windows "py" launcher no longer prevents startup.

REM 1) pythonw on PATH (best: no console window)
where pythonw >nul 2>nul
if not errorlevel 1 (
  pythonw -c "import tkinter" >nul 2>nul
  if not errorlevel 1 set "RUNNER=pythonw"
)

REM 2) py launcher, only if it really has Python 3 with tkinter
if not defined RUNNER (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -c "import tkinter" >nul 2>nul
    if not errorlevel 1 set "RUNNER=py -3"
  )
)

REM 3) pyw launcher
if not defined RUNNER (
  where pyw >nul 2>nul
  if not errorlevel 1 (
    pyw -3 -c "import tkinter" >nul 2>nul
    if not errorlevel 1 set "RUNNER=pyw -3"
  )
)

REM 4) python on PATH
if not defined RUNNER (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import tkinter" >nul 2>nul
    if not errorlevel 1 set "RUNNER=python"
  )
)

if not defined RUNNER (
  echo No usable Python 3 with tkinter was found.
  echo Install Python 3 from https://www.python.org and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

start "" %RUNNER% "%APP%"
exit /b 0
