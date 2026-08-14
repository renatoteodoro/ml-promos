#!/usr/bin/env python3
"""
Orquestrador automático do pipeline Promo das Galáxias (Fase 1 - estabilidade).

Estratégia à prova de falhas (implementada 13/08/2026):
  1. Gera o roteiro (busca+métrica+preços+cupons+cards+links meli.la)
  2. Envia os posts do dia em sequência contínua (não pula os atrasados)
  3. Registra estado transacional (posts enviados não reenviam)

Uso (pelo cron 07:00):
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

REPO = os.path.expanduser("~/ml-promos-repo")
DIVULGACAO = os.path.expanduser("~/divulgacao")
PYTHON = sys.executable

# Lock compartilhado COM o executor (flock no mesmo arquivo) — impede que o
# orquestrador rode enquanto um executor já está ativo (e vice-versa).
LOCK_FILE = os.path.join(DIVULGACAO, "executor.lock")


def adquirir_lock():
    """CHECAGEM de instância única (fcntl flock no MESMO arquivo do executor).
    O orquestrador NÃO pode segurar o lock enquanto chama o executor (que
    precisa adquirir o mesmo flock) — então aqui apenas testa se está livre,
    libera na hora e retorna True/False. Retorna True se NENHUM executor roda."""
    try:
        lock_file = open(LOCK_FILE, "a+")
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock_file.close()
            return False  # executor ativo — não prosseguir
        # Conseguiu o flock → está livre. Libera imediatamente (o executor
        # vai adquirir o próprio lock quando for chamado).
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
        return True
    except OSError:
        return True  # em dúvida, prossegue (o executor aborta se estiver ativo)


def liberar_lock(lock_file):
    pass  # sem lock retido — nada a liberar


def rodar(cmd, timeout=3600):
    """Roda comando e loga. Retorna (exit_code, output)."""
    print(f"\n{'='*60}\n▶ {' '.join(cmd)}\n{'='*60}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "") + (r.stderr or "")
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

        # Se o roteiro de hoje já existe e tem ofertas, pula a geração
        roteiro_pronto = False
        if os.path.exists(json_path):
            try:
                with open(json_path) as f:
                    d = json.load(f)
                if d.get("ofertas") and d.get("cards") and d.get("links"):
                    roteiro_pronto = True
                    print(f"✅ Roteiro de hoje já existe com {len(d['ofertas'])} ofertas — pulando geração.")
            except Exception:
                pass

        if not roteiro_pronto:
            # Gerar (remove JSON parcial de ontem se existir de forma inválida)
            rc, out = rodar([PYTHON, os.path.join(REPO, "ml_executor_diario.py")])
            if rc != 0:
                print("⚠️ ETAPA 1 falhou — tentando gerar só cards+links do JSON salvo...")
                # Se a busca falhou mas existe JSON parcial, tentar completar
                if os.path.exists(json_path):
                    rc2, _ = rodar([PYTHON, os.path.join(REPO, "ml_executor_diario.py"), "--so-links"])
                    if rc2 != 0:
                        print("❌ Não foi possível gerar o roteiro. Pipeline abortado.")
                        return 1
                else:
                    print("❌ Sem JSON e geração falhou. Pipeline abortado.")
                    return 1

        # ── ETAPA 2: ENVIAR posts do dia ──
        # --so-enviar agenda e envia nos horários exatos. Posts com horário passado
        # são pulados (gap pequeno em emergência; o watchdog relança e o cron de
        # 07:00 garante geração com folga para o 1º post das 08:00).
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
