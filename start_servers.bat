@echo off
title Quantum Learning - Start All Microservices
echo ===================================================
echo     Team Pluto - Quantum Learning Microservices
echo ===================================================

set ROOT=%~dp0
set ROOT=%ROOT:~0,-1%
set PYTHON=%ROOT%\web\backend\venv\Scripts\python.exe

echo [CLEANUP] Killing any old Python/Node worker processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM python3.12.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
ping -n 3 127.0.0.1 >nul
echo [CLEANUP] Done. All old servers stopped.
echo.

echo [1/7] Launching Pluto Backend (Port 5000)...
start "Pluto Backend - Port 5000" cmd /k "cd /d %ROOT%\web\backend && %PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 5000 --reload"
ping -n 3 127.0.0.1 >nul

echo [2/7] Launching Pluto Frontend (Port 5173)...
start "Pluto Frontend - Port 5173" cmd /k "cd /d %ROOT%\web\frontend && npm run dev"
ping -n 3 127.0.0.1 >nul

echo [3/7] Launching Mu Chatbot RAG (Port 8000)...
start "Mu Chatbot RAG - Port 8000" cmd /k "cd /d %ROOT%\chatbot\rag-engine && %PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 8000"
ping -n 3 127.0.0.1 >nul

echo [4/7] Launching Lambda Ingestion Service (Port 8001)...
start "Lambda Ingestion - Port 8001" cmd /k "cd /d %ROOT%\ai-ml && %PYTHON% -m uvicorn ingestion.main:app --host 0.0.0.0 --port 8001"
ping -n 3 127.0.0.1 >nul

echo [5/7] Launching Lambda Quiz Generator (Port 8002)...
start "Lambda Quiz Generator - Port 8002" cmd /k "cd /d %ROOT%\ai-ml && %PYTHON% -m uvicorn quiz_generator.app.main:app --host 0.0.0.0 --port 8002"
ping -n 3 127.0.0.1 >nul

echo [6/7] Launching Lambda Weak Topic Detection (Port 8003)...
start "Lambda Weak Topic Detection - Port 8003" cmd /k "cd /d %ROOT%\ai-ml && %PYTHON% -m uvicorn weak_topic_detection.app.main:app --host 0.0.0.0 --port 8003"
ping -n 3 127.0.0.1 >nul

echo [7/7] Launching Lambda Knowledge Graph (Port 8005)...
start "Lambda Knowledge Graph - Port 8005" cmd /k "cd /d %ROOT%\ai-ml && %PYTHON% -m uvicorn knowledge_graph.app.api.graph_routes:app --host 0.0.0.0 --port 8005"

echo.
echo ===================================================
echo   All 7 Microservices are launching!
echo.
echo   Frontend  : http://localhost:5173
echo   Backend   : http://localhost:5000
echo   Chatbot   : http://localhost:8000
echo   Ingestion : http://localhost:8001
echo   Quiz      : http://localhost:8002
echo   WeakTopic : http://localhost:8003
echo   KnowGraph : http://localhost:8005
echo ===================================================
pause