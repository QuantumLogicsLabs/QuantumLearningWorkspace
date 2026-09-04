@echo off
title Quantum Learning - Stop All Microservices
echo ===================================================
echo     Stopping All Microservices (Ports 5000, 5173, 8000, 8001, 8002, 8003)
echo ===================================================

echo Killing Python and Node processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM python3.12.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1

set ROOT=G:\Intern\QuantumLearningWorkspace_New
set PYTHON=%ROOT%\web\backend\.venv\Scripts\python.exe

%PYTHON% -c "import subprocess; ports = ['5000', '5173', '8000', '8001', '8002', '8003']; res = subprocess.run(['netstat', '-ano'], capture_output=True, text=True); pids = set(); [pids.add(line.split()[-1]) for line in res.stdout.splitlines() if any(f':{p}' in line for p in ports) and 'LISTENING' in line]; [subprocess.run(['taskkill', '/F', '/T', '/PID', pid], capture_output=True) for pid in pids]; print(f'Cleaned up any lingering port listeners.')"

echo ===================================================
echo   All microservices stopped cleanly!
echo ===================================================
pause
