#!/usr/bin/env python3
"""
Watchdog do pipeline Promo das Galáxias (Fase 1 - estabilidade).

Verifica a cada execução (cron */5) se o pipeline está saudável:
  1. Executor vivo? Se NÃO e ainda é horário de envio (08:00-23:30) → RELANÇA
  2. Roteiro de hoje existe? Se NÃO e já passou 07:45 → alerta (ação necessária)
  3. Último post enviado há quanto tempo? Se gap > 30 min em horário de envio → relança

Relançamento usa o orquestrador ml_pipeline_auto.py com --so-enviar (rápido, não
refaz cards/links). Silencioso quando tudo está ok.

Uso (cron): python3 pipeline_watchdog.py
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

REPO = os.path.expanduser("~/ml-promos-repo")
DIVULGACAO = os.path.expanduser("~/divulgacao")
PYTHON = sys.executable
LOG = "/tmp/ml_pipeline_watchdog.log"

# Janela de envio (08:00 às 23:30 — não relança fora dela)
JANELA_INICIO = "07:30"
JANELA_FIM = "23:30"


def log(msg):
    with open(LOG, "a") as f:
        f.write(f"{datetime.now().strftime('%H:%M:%S')} {msg}\n")


def executor_rodando():
    """True se ml_executor_diario ou ml_pipeline_auto está em execução."""
    try:
        r = subprocess.run(["pgrep", "-f", "ml_executor_diario.py|ml_pipeline_auto.py"],
                           capture_output=True, text=True, timeout=10)
        pids = [p for p in r.stdout.strip().split("\n") if p]
        # Excluir o próprio watchdog
        return len(pids) > 0
    except Exception:
        return True  # em dúvida, não age (evita duplicação)


def ultimo_post_hoje():
    """Timestamp do último HTTP 200 no log do dia. None se não houver."""
    hoje = datetime.now().date().isoformat()
    log_exec = f"/tmp/ml_exec_{hoje}.log"
    if not os.path.exists(log_exec):
        return None
    try:
        r = subprocess.run(["grep", "HTTP 200", log_exec], capture_output=True, text=True, timeout=10)
        linhas = [l for l in r.stdout.strip().split("\n") if l]
        if not linhas:
            return None
        ultima = linhas[-1]
        # Formato: "✅ Post 29 (10:56): HTTP 200"
        import re
        m = re.search(r"\((\d{2}:\d{2})\)", ultima)
        if m:
            hh, mm = map(int, m.group(1).split(":"))
            agora = datetime.now()
            return agora.replace(hour=hh, minute=mm, second=0, microsecond=0)
        return None
    except Exception:
        return None


def main():
    agora = datetime.now()
    hhmm = agora.strftime("%H:%M")
    hoje = agora.date().isoformat()
    log(f"verificação {hhmm}")

    # Fora da janela de envio: silencioso
    if hhmm < JANELA_INICIO or hhmm > JANELA_FIM:
        return 0

    roteiro = os.path.join(DIVULGACAO, f"roteiro_{hoje}.json")

    # CASO 1: Roteiro não existe e já passou 07:45 → alerta (precisa ação)
    if not os.path.exists(roteiro) and hhmm >= "07:45":
        print(f"🚨 PIPELINE PROMO: roteiro de hoje ({hoje}) NÃO foi gerado! "
              f"Verifique o cron das 07:00 e os logs. O grupo ficará sem ofertas hoje.")
        return 1

    # CASO 2: Executor morto em janela de envio → relança
    if not executor_rodando():
        # Ver se há posts enviados hoje (se sim, o executor terminou? só se após 23:30)
        ultimo = ultimo_post_hoje()
        gap_min = 999
        if ultimo:
            gap_min = (agora - ultimo).total_seconds() / 60
        if hhmm < "23:30":
            log(f"executor morto — relançando (último post há {gap_min:.0f} min)")
            print(f"⚠️ Pipeline Promo caiu (último post há {gap_min:.0f} min) — relançando...")
            # Relança com --so-enviar (rápido, não refaz cards/links)
            try:
                r = subprocess.Popen(
                    [PYTHON, os.path.join(REPO, "ml_executor_diario.py"), "--so-enviar"],
                    stdout=open(f"/tmp/ml_exec_{hoje}_watchdog.log", "a"),
                    stderr=subprocess.STDOUT,
                    start_new_session=True)
                log(f"relançado PID {r.pid}")
                print(f"🔄 Executor relançado (PID {r.pid}).")
            except Exception as e:
                log(f"ERRO ao relançar: {e}")
                print(f"❌ Não consegui relançar: {e}")
            return 0

    # CASO 3: Gap longo (executor vivo mas travado?) → relança
    if executor_rodando():
        ultimo = ultimo_post_hoje()
        if ultimo and (agora - ultimo).total_seconds() > 45 * 60 and hhmm < "23:00":
            log(f"gap de {(agora-ultimo).total_seconds()/60:.0f} min — executor pode estar travado")
            print(f"⚠️ Pipeline Promo: {((agora-ultimo).total_seconds()/60):.0f} min sem post — verificando...")
            # Não mata o executor (evita duplicação); apenas alerta
            print("🔍 Executor ainda vivo — monitorando. Se não voltar, relançar manualmente.")
            return 1

    # Tudo ok — silencioso
    return 0


if __name__ == "__main__":
    sys.exit(main())
