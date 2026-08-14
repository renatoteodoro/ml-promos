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


def ultimo_horario_roteiro(roteiro_path):
    """Último horário programado no roteiro do dia (ex: 23:00). None se inválido."""
    try:
        with open(roteiro_path) as f:
            d = json.load(f)
        # Horários vêm do gerador de horários (pode estar em 'posts', 'horarios' ou ofertas com horario)
        horarios = []
        if isinstance(d, dict):
            for chave in ("posts", "horarios", "ofertas"):
                itens = d.get(chave)
                if isinstance(itens, list):
                    for it in itens:
                        h = None
                        if isinstance(it, dict):
                            h = it.get("horario") or it.get("hora") or it.get("time")
                        elif isinstance(it, str):
                            h = it
                        if h and isinstance(h, str) and ":" in h:
                            horarios.append(h)
        if not horarios:
            return None
        horarios.sort()
        return horarios[-1]
    except Exception:
        return None


def dia_completo(roteiro_path, log_exec):
    """True se o dia terminou normalmente. Detecta pelo marcador '🏁 Concluído'
    no log do executor (impresso quando ele processa todo o roteiro) OU pelo
    último horário do roteiro já enviado com HTTP 200."""
    # Marcador principal: executor terminou o dia ("Concluído: N posts processados")
    try:
        if os.path.exists(log_exec):
            r = subprocess.run(["grep", "Concluído", log_exec], capture_output=True, text=True, timeout=10)
            if r.stdout.strip():
                return True
    except Exception:
        pass
    # Fallback: último horário do roteiro enviado com HTTP 200
    ult_hor = ultimo_horario_roteiro(roteiro_path)
    if not ult_hor:
        return False
    try:
        r = subprocess.run(["grep", "HTTP 200", log_exec], capture_output=True, text=True, timeout=10)
        for linha in r.stdout.split("\n"):
            if f"({ult_hor})" in linha and "HTTP 200" in linha:
                return True
    except Exception:
        pass
    return False


def roteiro_completo(roteiro_path):
    """True se o roteiro de hoje está COMPLETO (ofertas + cards + links meli.la).
    Roteiro incompleto (0 cards/0 links) indica geração abortada — NÃO relançar
    --so-enviar sobre ele (sairia sem imagem/link encurtado)."""
    try:
        with open(roteiro_path) as f:
            d = json.load(f)
        ofertas = d.get("ofertas") or []
        cards = d.get("cards") or []
        links = d.get("links") or []
        n_meli = sum(1 for l in links if l and "meli.la" in l)
        # Completo: tem ofertas, cards na mesma ordem e maioria dos links meli.la
        if not ofertas:
            return False
        if len(cards) < 100:
            return False
        if n_meli < 100:
            return False
        return True
    except Exception:
        return False


def main():
    agora = datetime.now()
    hhmm = agora.strftime("%H:%M")
    hoje = agora.date().isoformat()
    log(f"verificação {hhmm}")

    # Fora da janela de envio: silencioso
    if hhmm < JANELA_INICIO or hhmm > JANELA_FIM:
        return 0

    roteiro = os.path.join(DIVULGACAO, f"roteiro_{hoje}.json")
    log_exec = f"/tmp/ml_exec_{hoje}.log"

    # CASO 0: Dia já completou (último post do roteiro enviado) → SILENCIOSO, não relança
    if dia_completo(roteiro, log_exec):
        log(f"dia completo ({ultimo_horario_roteiro(roteiro)}) — sem ação")
        return 0

    # CASO 0.5: Roteiro incompleto (geração abortada) → NÃO relança com --so-enviar;
    # alerta pedindo regeneração (evita posts sem imagem/link meli.la).
    # ⚠️ Só alerta se NENHUM executor estiver rodando — se o executor está ativo,
    # a geração está EM ANDAMENTO e o roteiro pode estar momentaneamente incompleto.
    if os.path.exists(roteiro) and not roteiro_completo(roteiro) and not executor_rodando():
        log(f"roteiro INCOMPLETO (cards/links insuficientes) — sem relançamento")
        print(f"🚨 PIPELINE PROMO: roteiro de hoje ({hoje}) está INCOMPLETO "
              f"(cards/links não gerados). Posts sairiam sem imagem e sem link encurtado. "
              f"Regenerar: cd ~/ml-promos-repo && python3 ml_executor_diario.py --so-links "
              f"(após matar executor atual).")
        return 1

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
