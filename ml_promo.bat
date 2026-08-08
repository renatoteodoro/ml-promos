@echo off
REM Executa o ML Promos (chamado pelo Agendador do Windows)
cd /d "%~dp0"
python ml_promo.py --nicho "cama pet;racao pet;brinquedo pet;comedouro pet;arranhador;casinha pet" --desconto 15
