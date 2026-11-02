@echo off
rem Inicia a Atena.AI: banco (Docker), API e aplicacao cliente.
rem Antes de rodar, abra o Docker Desktop e espere o "Engine running".
cd /d "%~dp0"
echo Subindo o banco de dados...
docker compose up -d
echo Iniciando a API (janela separada)...
start "Atena.AI - API" cmd /k ".venv\Scripts\activate.bat && uvicorn src.api.main:app --port 8000"
echo Iniciando a aplicacao (janela separada)...
start "Atena.AI - Cliente" cmd /k ".venv\Scripts\activate.bat && streamlit run client/app.py"
echo.
echo Pronto. Aguarde a API mostrar "Application startup complete" e use o navegador.
pause
