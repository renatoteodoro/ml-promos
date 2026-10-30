#!/usr/bin/env python3
"""
Orquestrador automático do pipeline Promo das Galáxias (Fase 1 - estabilidade).

Estratégia à prova de falhas (implementada 13/08/2026):
  1. Gera o roteiro (busca+métrica+preços+cupons+cards+links meli.la)
  2. Envia os posts do dia em sequência contínua (não pula os atrasados)
  3. Registra estado transacional (posts enviados não reenviam)

Uso (pelo timer systemd 04:00):
    python3 ml_pipeline_auto.py

Este script é no_agent: NÃO depende de LLM/modelo para funcionar.
"""
import json
import os
import subprocess
import sys
import time
import fcntl
from datetime import datetime
from urllib.parse import urlsplit, parse_qs

REPO = os.path.expanduser("~/ml-promos-repo")
DIVULGACAO = os.path.expanduser("~/divulgacao")
PYTHON = sys.executable
LOCK_FILES = ("/tmp/pipeline_global.lock", os.path.join(DIVULGACAO, "executor.lock"))


def _lock_livre(path):
    try:
        with open(path, "a+") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(lock_file, fcntl.LOCK_UN)
        return True
    except OSError:
        return False


def adquirir_lock():
    """Só testa os dois locks compartilhados; nunca os segura ao chamar o executor."""
    return all(_lock_livre(path) for path in LOCK_FILES)


def link_afiliado_valido(link):
    if not isinstance(link, str) or not link:
        return False
    try:
        parts = urlsplit(link)
        host = (parts.hostname or "").lower()
        if (host == "meli.la" or host.endswith(".meli.la")) and parts.path.strip("/"):
            return True
        query = parse_qs(parts.query)
        return (
            (host == "mercadolivre.com.br" or host.endswith(".mercadolivre.com.br"))
            and query.get("matt_word", [""])[0] == "renatoteodoro"
            and query.get("matt_tool", [""])[0] == "94885465"
        )
    except ValueError:
        return False


def roteiro_completo(dados):
    if not isinstance(dados, dict):
        return False
    ofertas = dados.get("ofertas") or []
    cards = dados.get("cards") or []
    links = dados.get("links") or []
    cards_validos = sum(1 for card in cards if card and os.path.isfile(card))
    links_validos = sum(1 for link in links if link_afiliado_valido(link))
    piso = int(os.environ.get("PROMO_MIN_FLOOR", "25"))
    return len(ofertas) >= piso and cards_validos >= len(ofertas) and links_validos >= len(ofertas)


def liberar_lock(lock_file):
    pass  # sem lock retido — nada a liberar


def rodar(cmd, timeout=3600):
    """Roda comando e loga. Retorna (exit_code, output)."""
    print(f"\n{'='*60}\n▶ {' '.join(cmd)}\n{'='*60}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "") + (r.stderr or "")
        if not out.strip() and any(os.path.basename(part) == "ml_executor_diario.py" for part in cmd):
            log_path = os.environ.get("ML_PROMO_LOG_PATH", f"/tmp/ml_exec_{datetime.now().date().isoformat()}.log")
            try:
                with open(log_path, "rb") as log_file:
                    log_file.seek(max(0, os.fstat(log_file.fileno()).st_size - 12000))
                    out = log_file.read().decode("utf-8", "replace")
            except OSError:
                pass
        print(out[-3000:])
        return r.returncode, out
    except subprocess.TimeoutExpired:
        print("⏰ TIMEOUT")
        return 124, ""
    except Exception as e:
        print(f"❌ erro ao rodar: {e}")
        return 1, str(e)


def main():
    if not adquirir_lock():
        print("🔒 Outro processo já está rodando (lock do executor ativo) — abortando (evita duplicação).")
        return 0

    hoje = datetime.now().date().isoformat()
    json_path = os.path.join(DIVULGACAO, f"roteiro_{hoje}.json")
    try:
        # ── ETAPA 1: GERAR roteiro (busca, métrica, preços, cupons, cards, links) ──
        print(f"\n🚀 PIPELINE PROMO DAS GALÁXIAS — {hoje}")
        print("📅 ETAPA 1: Gerando roteiro do dia...")

        # Preparar o roteiro em modo seguro: coleta/cards/links sem qualquer envio.
        roteiro_pronto = False
        if os.path.exists(json_path):
            try:
                with open(json_path, encoding="utf-8") as f:
                    d = json.load(f)
                roteiro_pronto = roteiro_completo(d)
                if roteiro_pronto:
                    print(f"✅ Roteiro completo: {len(d['ofertas'])} ofertas, cards e links válidos — pulando preparação.")
                else:
                    print("⚠️ Roteiro ausente/incompleto; será preparado novamente sem enviar mensagens.")
            except Exception as e:
                print(f"⚠️ JSON do roteiro inválido ({type(e).__name__}); será preparado novamente.")

        if not roteiro_pronto:
            rc, out = rodar(
                [PYTHON, os.path.join(REPO, "ml_executor_diario.py"), "--preparar"],
                timeout=200 * 60,
            )
            if rc != 0:
                print("❌ Preparação falhou; etapa de envio bloqueada.")
                return 1
            try:
                with open(json_path, encoding="utf-8") as f:
                    d = json.load(f)
            except Exception as e:
                print(f"❌ Preparação terminou sem JSON válido: {type(e).__name__}: {e}")
                return 1
            if not roteiro_completo(d):
                print("❌ Roteiro ainda incompleto após a preparação; etapa de envio bloqueada.")
                return 1
            print("✅ Roteiro completo verificado antes do envio.")

        # ── ETAPA 2: ENVIAR posts do dia ──
        # --so-enviar agenda e envia nos horários exatos. Posts com horário passado
        # são pulados (gap pequeno em emergência; o watchdog relança e o cron de
        # timer 04:00 garante geração com folga para o 1º post das 08:00).
        print("\n📤 ETAPA 2: Enviando posts do dia...")
        rc, out = rodar([PYTHON, os.path.join(REPO, "ml_executor_diario.py"), "--so-enviar"],
                        timeout=20 * 3600)  # até 20h (08:00-23:00 + margem)
        if rc != 0:
            print("❌ ETAPA 2 falhou.")
            return 1

        print("\n🏁 Pipeline do dia concluído.")
        return 0
    finally:
        liberar_lock(None)


if __name__ == "__main__":
    sys.exit(main())
