@echo off
setlocal enabledelayedexpansion

REM ==============================================================================
REM epub2audiobook - Instalador e Inicializador Automático Local (Windows)
REM ==============================================================================

echo ==========================================================
echo    epub2audiobook - Inicializador Local (PT-BR)
echo ==========================================================

REM 1. Verifica se o Python esta instalado
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERRO] Python nao encontrado no PATH do sistema.
    echo Por favor instale o Python 3.10 ou superior e marque a opcao "Add Python to PATH".
    pause
    exit /b 1
)

REM 2. Cria o ambiente virtual venv se nao existir
if not exist "venv" (
    echo [1/3] Criando ambiente virtual Python (venv)...
    python -m venv venv
)

REM 3. Ativa o ambiente virtual
call venv\Scripts\activate

REM 4. Instala ou atualiza as dependencias
echo [2/3] Verificando dependencias do projeto...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

REM 5. Inicia a interface grafica Web
echo [3/3] Iniciando interface Web em http://localhost:8501 ...
echo Pressione Ctrl+C na janela para encerrar.
python cli.py ui --porta 8501

pause
