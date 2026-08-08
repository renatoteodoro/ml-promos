@echo off
REM ============================================================
REM  INSTALADOR DO ML PROMOS — Windows 11
REM  Rode como:  clique 2x neste arquivo (ou: install.bat)
REM  O que faz:
REM    1. Verifica se Python está instalado
REM    2. Testa o script manualmente
REM    3. Agenda a tarefa (10h e 20h) no Agendador do Windows
REM ============================================================
cd /d "%~dp0"

echo.
echo ==========================================
echo   ML PROMOS - Instalador Windows
echo ==========================================
echo.

REM 1. Verificar Python
where python >nul 2>nul
if %errorlevel%==0 (
    echo [OK] Python encontrado:
    python --version
) else (
    echo [ERRO] Python nao encontrado!
    echo Baixe em https://www.python.org/downloads/
    echo IMPORTANTE: marque a opcao "Add Python to PATH" na instalacao.
    pause
    exit /b 1
)

REM 2. Verificar token
if exist "mcp-tokens\mercadolibre.token.json" (
    echo [OK] Token encontrado em mcp-tokens\
) else (
    echo [AVISO] Token NAO encontrado em mcp-tokens\
    echo Copie a pasta mcp-tokens (com o arquivo mercadolibre.token.json)
    echo para esta mesma pasta antes de continuar.
    echo.
    echo Se ja copiou, pressione qualquer tecla para continuar...
    pause >nul
)

REM 3. Testar script
echo.
echo [TESTE] Rodando busca de teste (3 segundos de rede)...
python ml_promo.py --nicho "cama pet" --limite 2 --desconto 0
if %errorlevel%==0 (
    echo [OK] Script funcionou!
) else (
    echo [ATENCAO] Script retornou erro - veja a mensagem acima.
    echo Verifique a TAG de afiliado e o token antes de agendar.
    echo.
    echo Pressione qualquer tecla para continuar mesmo assim...
    pause >nul
)

REM 4. Agendar tarefa (10h e 20h)
echo.
echo [AGENDAR] Criando tarefa no Agendador do Windows...
schtasks /create /tn "ML Promos" /tr "\"%~dp0ml_promo.bat\"" /sc daily /st 10:00 /f
schtasks /create /tn "ML Promos 20h" /tr "\"%~dp0ml_promo.bat\"" /sc daily /st 20:00 /f

echo.
echo ==========================================
echo   INSTALACAO CONCLUIDA!
echo ==========================================
echo.
echo O script rodara automaticamente as 10h e 20h.
echo Para testar manualmente agora:
echo     python ml_promo.py --nicho "cama pet" --desconto 15
echo.
pause
