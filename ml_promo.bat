@echo off
REM Executa o ML Promos (chamado pelo Agendador do Windows)
cd /d "%~dp0"
python ml_promo.py --ofertas-do-dia --desconto 15
