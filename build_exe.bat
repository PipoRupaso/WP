@echo off
setlocal
cd /d "%~dp0"
title Build game to EXE
echo ============================================
echo  Building PixelZomboidProto.exe
echo ============================================
echo .

REM Prefer Python 3.13 / 3.12 / 3.11: pygame has no ready
REM packages for Python 3.14 yet, so 3.14 cannot be used.
py -3.13 --version >nul 2>&1
if %errorlevel%==0 goto use_313
py -3.12 --version >nul 2>&1
if %errorlevel%==0 goto use_312
py -3.11 --version >nul 2>&1
if %errorlevel%==0 goto use_311
py --version >nul 2>&1
if %errorlevel%==0 goto use_py
python --version >nul 2>&1
if %errorlevel%==0 goto use_python
goto no_python

:use_313
set PYCMD=py -3.13
goto check_done

:use_312
set PYCMD=py -3.12
goto check_done

:use_311
set PYCMD=py -3.11
goto check_done

:use_py
set PYCMD=py
goto check_done

:use_python
set PYCMD=python
goto check_done

:no_python
set PYVER=none
goto need_313

:check_done
echo [OK] Found Python:
%PYCMD% --version
REM Detect version via temp file (robust, no nested execution).
%PYCMD% --version > "%TEMP%\zmver.txt" 2>&1
set PYVER=
for /f "usebackq tokens=2" %%A in ("%TEMP%\zmver.txt") do set PYVER=%%A
if "%PYVER%"=="" (
  echo [ERROR] Could not detect Python version.
  pause
  exit /b 1
)
echo %PYVER% | findstr /c:"3.13." /c:"3.12." /c:"3.11." >nul
if %errorlevel%==0 goto version_ok
goto need_313

:need_313
echo .
if "%PYVER%"=="none" (
  echo [INFO] No Python found. Installing Python 3.13 automatically ...
) else (
  echo [INFO] Found Python %PYVER%, but pygame needs Python 3.11 - 3.13.
  echo [INFO] Installing Python 3.13 automatically, old version stays.
)
echo .
echo [AUTO] Step 1 of 2: trying "py install 3.13" ...
py install 3.13
py -3.13 --version >nul 2>&1
if %errorlevel%==0 (
  echo [OK] Python 3.13 installed.
  set PYCMD=py -3.13
  goto check_done
)
echo [WARN] "py install" did not work.
echo .
echo [AUTO] Step 2 of 2: trying winget install ...
winget --version >nul 2>&1
if not %errorlevel%==0 (
  echo [WARN] winget not found.
  goto manual_install
)
winget install -e --id Python.Python.3.13 --silent --accept-package-agreements --accept-source-agreements
py -3.13 --version >nul 2>&1
if %errorlevel%==0 (
  echo [OK] Python 3.13 installed.
  set PYCMD=py -3.13
  goto check_done
)
echo [WARN] winget install failed.
goto manual_install

:manual_install
echo .
echo [ERROR] Automatic install failed. Please install Python 3.13 by hand:
echo   https://www.python.org/downloads/
echo Open "Looking for a specific release?", choose Python 3.13,
echo download "Windows installer (64-bit)" and run it.
echo Or run this in terminal: py install 3.13
echo No need to uninstall other versions.
echo .
echo After install run this file again.
pause
exit /b 1

:version_ok
echo [OK] Version %PYVER% is good.
REM Resolve the real python.exe via a tiny probe script
REM (no -c one-liner: some setups block or mangle it).
echo import sys> "%TEMP%\zmprobe.py"
echo print(sys.executable)>> "%TEMP%\zmprobe.py"
set PYEXE=
%PYCMD% "%TEMP%\zmprobe.py" > "%TEMP%\zmexe.txt" 2>nul
for /f "usebackq delims=" %%A in ("%TEMP%\zmexe.txt") do set PYEXE=%%A
if "%PYEXE%"=="" (
  echo [WARN] Path probe came back empty, retrying once ...
  timeout /t 2 /nobreak >nul
  %PYCMD% "%TEMP%\zmprobe.py" > "%TEMP%\zmexe.txt" 2>nul
  for /f "usebackq delims=" %%A in ("%TEMP%\zmexe.txt") do set PYEXE=%%A
)
if not "%PYEXE%"=="" if exist "%PYEXE%" goto resolved_ok
REM Second try: parse the launcher list "py -0p".
set PYEXE=
py -0p > "%TEMP%\zmlist.txt" 2>nul
set SHORT=%PYVER:~0,4%
for /f "usebackq tokens=1*" %%A in ("%TEMP%\zmlist.txt") do if "%%A"=="-%SHORT%-64" set "PYEXE=%%B"
if "%PYEXE%"=="" for /f "usebackq tokens=1*" %%A in ("%TEMP%\zmlist.txt") do if "%%A:~1,4%"=="%SHORT%" set "PYEXE=%%B"
if not "%PYEXE%"=="" if "%PYEXE:~-2%"==" *" set "PYEXE=%PYEXE:~0,-2%"
if not "%PYEXE%"=="" if exist "%PYEXE%" goto resolved_ok
REM Last resort: use the launcher itself (may still work).
echo [WARN] Could not resolve python.exe path, using launcher: %PYCMD%
echo        If the build fails: run as Administrator, move the folder
echo        out of Downloads, or pause antivirus and retry.
echo .
set PYRUN=%PYCMD%
goto run_ready

:resolved_ok
echo [OK] Using: %PYEXE%
set PYRUN="%PYEXE%"

:run_ready
echo .

echo [1 of 3] Installing pygame, numpy, pyinstaller ...
call :tryrun pip -m pip install --upgrade pygame numpy pyinstaller
if not %errorlevel%==0 (
  echo [ERROR] Could not install libraries. Try: run as Administrator,
  echo move the folder out of Downloads, pause antivirus, check internet.
  pause
  exit /b 1
)
echo .

echo [2 of 3] Running game self-test ...
call :tryrun test main.py --test
if not %errorlevel%==0 (
  echo [ERROR] Self-test failed. Send the text above to the developer.
  pause
  exit /b 1
)
echo .

echo [3 of 3] Building EXE, please wait 1-3 minutes ...
REM Fresh build dir (ignore errors if files are locked).
rmdir /s /q build 2>nul
del /q PixelZomboidProto.spec 2>nul
call :tryrun build -m PyInstaller --onefile --windowed --name PixelZomboidProto main.py
if not %errorlevel%==0 (
  echo [ERROR] Build failed. Try: run as Administrator, move the folder
  echo out of Downloads, pause antivirus. Then send the log to the developer.
  pause
  exit /b 1
)

:build_ok
echo .
echo ============================================
echo  DONE! Your game: dist\PixelZomboidProto.exe
echo  Double-click it to play.
echo ============================================
pause
exit /b 0

REM Runs a python step up to 3 times: direct exe, launcher, direct again.
REM Usage: call :tryrun TAG arg1 arg2 ...
:tryrun
%PYRUN% %2 %3 %4 %5 %6 %7 %8 %9
if %errorlevel%==0 exit /b 0
echo [WARN] Attempt failed (%1), retrying another way ...
%PYCMD% %2 %3 %4 %5 %6 %7 %8 %9
if %errorlevel%==0 exit /b 0
echo [WARN] Still failing (%1), one last try in 3 seconds ...
timeout /t 3 /nobreak >nul
%PYRUN% %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%
