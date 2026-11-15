@echo off
rem Copyright 2026 Vinay Williams
rem
rem Installs the Rocketry P&ID symbol library into KiCad (Windows).
rem Double-click it, or run it from a command prompt. Arguments are passed
rem on to install.py, for example --dry-run or --uninstall.
setlocal

set "SCRIPT=%~dp0install.py"
if not exist "%SCRIPT%" set "SCRIPT=%~dp0scripts\install.py"

set "PYTHON="
py -3 --version >nul 2>nul && set "PYTHON=py -3"
if not defined PYTHON python --version >nul 2>nul && set "PYTHON=python"
if not defined PYTHON goto nopython

%PYTHON% "%SCRIPT%" %*
set "STATUS=%ERRORLEVEL%"
goto finish

:nopython
echo Rocketry P^&ID KiCAD - Install
echo.
echo Python 3 was not found, and the installer needs it.
echo Either install Python 3 from https://www.python.org/downloads/ and run this again,
echo or skip Python: in KiCad open Plugin and Content Manager, choose
echo Install from File and pick the kicad_pid-*.zip file from the release page.
set "STATUS=1"

:finish
rem Started by double-click, the window closes when the script ends, so wait
echo %cmdcmdline% | find /i "/c" >nul && pause
exit /b %STATUS%
