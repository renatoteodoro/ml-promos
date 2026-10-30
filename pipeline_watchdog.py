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
import fcntl
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from urllib.parse import urlsplit, parse_qs

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


def alertar_uma_vez(hoje, chave, mensagem):
    marcador = f"/tmp/pipeline_watchdog_{hoje}_{chave}.sent"
    if os.path.exists(marcador):
        log(f"alerta {chave} já enviado hoje; suprimindo repetição")
        return False
    try:
        with open(marcador, "w") as f:
            f.write(datetime.now().isoformat())
    except OSError:
        pass
    print(mensagem)
    return True


def limpar_alerta(hoje, chave):
    try:
        os.unlink(f"/tmp/pipeline_watchdog_{hoje}_{chave}.sent")
    except FileNotFoundError:
        pass
    except OSError:
        pass


def instancia_pipeline_ativa():
    """True se outro processo segura o lock global do pipeline."""
    try:
        with open("/tmp/pipeline_global.lock", "a+") as probe:
            try:
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                return True
            fcntl.flock(probe, fcntl.LOCK_UN)
            return False
    except OSError:
        return True  # falha fechada: não arriscar um segundo executor


def executor_rodando():
    """Detecta os scripts reais em /proc, sem pgrep casar com o próprio watchdog."""
    targets = {"ml_executor_diario.py", "ml_pipeline_auto.py"}
    try:
        for entry in os.scandir("/proc"):
            if not entry.name.isdigit() or int(entry.name) == os.getpid():
                continue
            try:
                with open(os.path.join(entry.path, "cmdline"), "rb") as f:
                    argv = [part.decode("utf-8", "ignore") for part in f.read().split(b"\0") if part]
            except (OSError, ProcessLookupError):
                continue
            if any(os.path.basename(arg) in targets for arg in argv):
                return True
    except OSError:
        return True  # em dúvida, não iniciar outro processo
    return instancia_pipeline_ativa()


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


def roteiro_completo(roteiro_path):
    """Aceita roteiro completo ou enxuto acima do piso, sempre com card e link por oferta."""
    try:
        with open(roteiro_path, encoding="utf-8") as f:
            dados = json.load(f)
        ofertas = dados.get("ofertas") or []
        cards = dados.get("cards") or []
        links = dados.get("links") or []
        n_cards = sum(1 for card in cards if card and os.path.isfile(card))
        n_links = sum(1 for link in links if link_afiliado_valido(link))
        piso = int(os.environ.get("PROMO_MIN_FLOOR", "25"))
        return len(ofertas) >= piso and n_cards >= len(ofertas) and n_links >= len(ofertas)
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

    if roteiro_completo(roteiro):
        limpar_alerta(hoje, "incompleto")
        limpar_alerta(hoje, "ausente")

    # CASO 0: Dia já completou (último post do roteiro enviado) → SILENCIOSO, não relança
    if dia_completo(roteiro, log_exec):
        log(f"dia completo ({ultimo_horario_roteiro(roteiro)}) — sem ação")
        return 0

    # Roteiro incompleto só é falha quando não há preparação ativa; alertar uma vez.
    if os.path.exists(roteiro) and not roteiro_completo(roteiro) and not executor_rodando():
        log("roteiro INCOMPLETO (ofertas/cards/links inválidos) — sem relançamento")
        alertar_uma_vez(
            hoje,
            "incompleto",
            f"🚨 PIPELINE PROMO: roteiro de hoje ({hoje}) está INCOMPLETO "
            f"(ofertas abaixo do piso ou cards/links inválidos). Nenhuma mensagem será enviada. "
            f"Regenerar com: cd ~/ml-promos-repo && python3 ml_executor_diario.py --preparar",
        )
        return 0

    # Sem roteiro após 07:45 só é alerta se a preparação realmente parou.
    if not os.path.exists(roteiro) and hhmm >= "07:45" and not executor_rodando():
        alertar_uma_vez(
            hoje,
            "ausente",
            f"🚨 PIPELINE PROMO: roteiro de hoje ({hoje}) não foi gerado. "
            f"Nenhuma mensagem será enviada até a preparação completar.",
        )
        return 0

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

    # CASO 3: Gap longo (executor vivo mas travado?) → alerta uma vez, sem marcar erro no cron
    if executor_rodando():
        ultimo = ultimo_post_hoje()
        if ultimo and (agora - ultimo).total_seconds() > 45 * 60 and hhmm < "23:00":
            minutos = (agora - ultimo).total_seconds() / 60
            log(f"gap de {minutos:.0f} min — executor pode estar travado")
            alertar_uma_vez(
                hoje,
                "gap",
                f"⚠️ Promo das Galáxias: sem postagem há {minutos:.0f} min; o executor segue ativo. Verificar o log antes de reiniciar.",
            )
            return 0
        limpar_alerta(hoje, "gap")

    # Tudo ok — silencioso
    return 0


if __name__ == "__main__":
    sys.exit(main())
