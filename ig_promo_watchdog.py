#!/usr/bin/env python3
"""
Watchdog silencioso da automação do Instagram da Promo das Galáxias.

Verifica se os stories/feed programados foram publicados. Só imprime (e alerta)
quando algo NÃO funcionou. Silencioso quando tudo está ok.

Horários esperados: Story 08:30, Feed 09:00, Story 12:00, Story 16:30,
                    Feed 19:30, Story 21:00

Uso: python3 ig_promo_watchdog.py [--hora HH:MM]  # opcional, hora específica
"""
import json
import os
import sys
import subprocess
from datetime import datetime

DIVULGACAO = os.path.expanduser("~/divulgacao")
STATE_FILE = os.path.join(DIVULGACAO, "promo-galaxias", "insta_state.json")


def main():
    agora = datetime.now()
    hoje = agora.date().isoformat()

    # Roteiro de hoje existe? (o cron das 07:00 gera) — só alertar após 07:30
    roteiro = os.path.join(DIVULGACAO, f"roteiro_{hoje}.json")
    if not os.path.exists(roteiro) and agora.strftime("%H:%M") >= "07:30":
        print(f"⚠️ IG Promo: roteiro de hoje ({hoje}) não existe — pipeline ML não rodou às 07:00?")
        return 1

    # State das publicações
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
    else:
        state = {}

    postados = set(state.get("postados", []))
    stories = set(state.get("stories_postados", []))
    hora_atual = agora.strftime("%H:%M")

    # Verificação por horário (apenas após o horário esperado + margem)
    problemas = []

    def verificar(hora_esperada, tipo, indice_set, rotulo):
        if hora_atual >= hora_esperada:
            if len(indice_set) == 0:
                problemas.append(f"{rotulo} ({hora_esperada}): nenhuma publicação detectada")

    verificar("08:45", "Story 08:30", stories, "Story 08:30")
    verificar("09:15", "Feed 09:00", postados, "Feed 09:00")
    verificar("12:15", "Story 12:00", stories, "Story 12:00")
    verificar("16:45", "Story 16:30", stories, "Story 16:30")
    verificar("19:45", "Feed 19:30", postados, "Feed 19:30")
    verificar("21:15", "Story 21:00", stories, "Story 21:00")

    if problemas:
        print(" | ".join(problemas))
        return 1
    # Tudo ok — silencioso
    return 0


if __name__ == "__main__":
    sys.exit(main())
