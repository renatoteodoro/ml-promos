#!/usr/bin/env python3
"""
Executor diário "Promo das Galáxias" — busca 102 ofertas reais, gera cards,
agenda e envia as 100 postagens nos horários exatos do roteiro.

Fluxo:
1. Busca ofertas do dia (paginação /ofertas até 102+ únicas)
2. Gera card para cada oferta (Playwright, batch)
3. Gera links meli.la via Gerador de Links do portal (sessão salva)
4. Agenda os 100 envios nos horários do roteiro (asyncio)
5. Envia card+texto (posts 2-99) e texto puro (posts 1 e 100)

Uso: python3 ml_executor_diario.py [--dry-run] [--forcar-horario HH:MM]
"""
import os, sys, json, time, asyncio, argparse, subprocess, datetime, re, fcntl
import os as _envos
MINIMO = int(_envos.environ.get("PROMO_MIN_OFERTAS", "140"))
MIN_FLOOR = int(_envos.environ.get("PROMO_MIN_FLOOR", "25"))  # chao: nunca zera o grupo
from urllib.parse import urlsplit, urlunsplit, parse_qsl, parse_qs, urlencode

REPO = os.path.expanduser("~/ml-promos-repo")
VENV_PY = os.path.expanduser("~/.hermes/hermes-agent/venv/bin/python3")
DIVULGACAO = os.path.abspath(os.path.expanduser(os.environ.get("ML_PROMO_OUTPUT_DIR", "~/divulgacao")))
GRUPO = os.environ.get("PROMO_GRUPO", "120363428591609827@g.us")
BRIDGE = os.environ.get("PROMO_BRIDGE", "http://127.0.0.1:3000")
BRIDGE_TOKEN_FILE = os.path.expanduser("~/.hermes/whatsapp/session/.bridge-token")
NATAL_FIM = datetime.date(2026, 12, 20)
NATAL_PERCENTUAL = float(os.environ.get("PROMO_NATAL_PERCENTUAL", "0.40"))
NATAL_TERMOS = (
    "natal", "enfeite", "ornamento", "árvore de natal", "pisca-pisca",
    "pisca pisca", "luzes de natal", "guirlanda", "presépio",
    "bola de natal", "fita natalina", "estrela de natal",
)


def natal_ativo(data=None):
    try:
        atual = datetime.date.fromisoformat(str(data)[:10]) if data else datetime.date.today()
    except ValueError:
        atual = datetime.date.today()
    return atual <= NATAL_FIM


def eh_oferta_natal(oferta):
    titulo = str(oferta.get("titulo", "")).casefold()
    return any(termo in titulo for termo in NATAL_TERMOS)


def selecionar_ofertas_com_natal(ofertas, n_desejado, ja_postados, data):
    """Reserva 40% das ofertas para enfeites natalinos, quando disponíveis."""
    if not natal_ativo(data):
        return filtrar_por_metrica(ofertas, n_desejado=n_desejado, ja_postados=ja_postados)

    percentual = min(max(NATAL_PERCENTUAL, 0.0), 1.0)
    meta_natal = min(n_desejado, int(round(n_desejado * percentual)))
    natal = [o for o in ofertas if eh_oferta_natal(o)]
    sazonais = filtrar_por_metrica(
        natal,
        n_desejado=meta_natal,
        ja_postados=ja_postados,
    )
    chaves_sazonais = {
        str(o.get("catalog_id") or o.get("product_id") or o.get("link", ""))
        for o in sazonais
    }
    gerais = [
        o for o in ofertas
        if not eh_oferta_natal(o)
        and str(o.get("catalog_id") or o.get("product_id") or o.get("link", ""))
        not in chaves_sazonais
    ]
    restantes = filtrar_por_metrica(
        gerais,
        n_desejado=max(0, n_desejado - len(sazonais)),
        ja_postados=ja_postados,
    )
    selecionadas = sazonais + restantes
    selecionadas_chaves = {
        str(o.get("catalog_id") or o.get("product_id") or o.get("link", ""))
        for o in selecionadas
    }
    if len(selecionadas) < n_desejado:
        base = filtrar_por_metrica(
            [o for o in ofertas if not eh_oferta_natal(o)],
            n_desejado=n_desejado,
            ja_postados=ja_postados,
        )
        for oferta in base:
            chave = str(oferta.get("catalog_id") or oferta.get("product_id") or oferta.get("link", ""))
            if chave not in selecionadas_chaves:
                selecionadas.append(oferta)
                selecionadas_chaves.add(chave)
            if len(selecionadas) >= n_desejado:
                break

    for oferta in selecionadas:
        if eh_oferta_natal(oferta):
            oferta["promo_sazonal"] = "natal"
    natal_selecionadas = sum(1 for oferta in selecionadas if oferta.get("promo_sazonal") == "natal")
    percentual_real = natal_selecionadas / max(len(selecionadas), 1)
    print(f"🎄 Natal: {natal_selecionadas}/{len(selecionadas)} ofertas ({percentual_real:.0%} quando há candidatos válidos) | meta {meta_natal}/{n_desejado}")
    if natal_selecionadas < meta_natal:
        print(f"⚠️ Natal: só {natal_selecionadas} candidatos válidos passaram pelos filtros; não vou repetir nem inventar ofertas.")
    return selecionadas[:n_desejado]


def bridge_headers():
    headers = {"Content-Type": "application/json"}
    try:
        with open(BRIDGE_TOKEN_FILE, encoding="utf-8") as f:
            token = f.read().strip()
    except OSError:
        token = ""
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


sys.path.insert(0, REPO)
from ml_promo import extrair_ofertas_html
from ml_roteiro_diario import HORARIOS, construir_roteiro
from ml_metrica import (filtrar_por_metrica, carregar_historico, registrar_posts,
                        resumo_metrica, links_ja_postados_no_cooldown,
                        REPETICAO_COOLDOWN_DIAS)
from ml_compare_preco import enriquecer_lote
from ml_detectar_cupons import processar as detectar_cupons_lote

AFFILIATE_WORD = "renatoteodoro"
AFFILIATE_TOOL = "94885465"


def link_afiliado_valido(link):
    """Aceita meli.la oficial ou URL direta com a tag completa do afiliado."""
    if not isinstance(link, str) or not link:
        return False
    try:
        parts = urlsplit(link)
        host = (parts.hostname or "").lower()
        if host == "meli.la" or host.endswith(".meli.la"):
            return bool(parts.path.strip("/"))
        query = parse_qs(parts.query)
        return (
            host == "mercadolivre.com.br" or host.endswith(".mercadolivre.com.br")
        ) and query.get("matt_word", [""])[0] == AFFILIATE_WORD and query.get("matt_tool", [""])[0] == AFFILIATE_TOOL
    except ValueError:
        return False


def link_direto_afiliado(url):
    """Acrescenta a tag oficial sem remover filtros como pdp_filters=item_id."""
    if not isinstance(url, str) or not url:
        return ""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if not (host == "mercadolivre.com.br" or host.endswith(".mercadolivre.com.br")):
            return ""
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if k not in ("matt_word", "matt_tool")]
        query.extend((("matt_word", AFFILIATE_WORD), ("matt_tool", AFFILIATE_TOOL)))
        return urlunsplit(("https", parts.netloc, parts.path, urlencode(query), parts.fragment))
    except ValueError:
        return ""


def buscar_98_ofertas(ja_postados=None, ids_postados=None,
                      cooldown_days=REPETICAO_COOLDOWN_DIAS):
    """Busca ofertas HTML e completa por API oficial quando a coleta é bloqueada/curta."""
    from ml_api_source import buscar_ofertas_highlights, catalog_id_from_url, PESQUISAS_NATALINAS

    termos_prioritarios = PESQUISAS_NATALINAS if natal_ativo() else ()
    todas, links_vistos = [], set()
    for pg in range(1, 15):
        try:
            ofs = extrair_ofertas_html(f"https://www.mercadolivre.com.br/ofertas?page={pg}")
        except Exception as e:
            print(f"  ⚠️ Página {pg}: {e}")
            break
        novas = [o for o in ofs if o.get("link") and o["link"] not in links_vistos]
        for o in novas:
            links_vistos.add(o["link"])
        todas.extend(novas)
        print(f"  Página {pg}: +{len(novas)} (total {len(todas)})")
        if not novas:
            print("  ⚠️ Nenhuma oferta nova na página; interrompendo a coleta HTML e usando a contingência oficial.")
            break
        if len(todas) >= 300:
            break
        time.sleep(0.5)

    ja_postados = set(ja_postados or ())
    ids_postados = {str(x).upper() for x in (ids_postados or ())}
    novidade = []
    ids_da_coleta = set()
    for oferta in todas:
        pid = catalog_id_from_url(oferta.get("link", ""))
        if pid:
            ids_da_coleta.add(pid)
        if oferta.get("link") not in ja_postados and (not pid or pid not in ids_postados):
            novidade.append(oferta)
    if len(novidade) >= 300:
        return todas

    necessario = max(MINIMO, 300 - len(novidade))
    print(f"  🔁 Coleta HTML trouxe {len(novidade)} ofertas não repetidas; completando até {necessario} pela API oficial.")
    api_ofertas = buscar_ofertas_highlights(
        DIVULGACAO,
        history_links=ja_postados,
        extra_ids=ids_postados | ids_da_coleta,
        limite_ofertas=necessario,
        cooldown_days=cooldown_days,
        termos_prioritarios=termos_prioritarios,
    )
    print(f"  API oficial acrescentou {len(api_ofertas)} ofertas verificadas.")
    return todas + api_ofertas

def gerar_cards_batch(ofertas):
    """Gera cards para todas as ofertas (uma sessão Playwright)."""
    import base64, urllib.request
    from playwright.sync_api import sync_playwright

    cards = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage", "--no-sandbox",
            "--js-flags=--max-old-space-size=256",
        ])
        page = browser.new_page(viewport={"width": 1080, "height": 1080})
        for i, oferta in enumerate(ofertas):
            try:
                # Tentar até quatro imagens oficiais do produto, sem publicar card vazio.
                foto_urls = oferta.get("imagens") or [oferta.get("imagem", "")]
                foto_b64 = ""
                foto_mime = ""
                for foto_url in [u for u in foto_urls if u][:4]:
                    try:
                        req = urllib.request.Request(foto_url, headers={
                            "User-Agent": "Mozilla/5.0",
                            "Referer": "https://www.mercadolivre.com.br/",
                            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                        })
                        with urllib.request.urlopen(req, timeout=15) as r:
                            raw = r.read()
                            mime = r.headers.get_content_type()
                        if not raw:
                            continue
                        if not mime.startswith("image/"):
                            import mimetypes
                            mime = mimetypes.guess_type(foto_url)[0] or "image/jpeg"
                        foto_b64 = base64.b64encode(raw).decode()
                        foto_mime = mime
                        break
                    except Exception:
                        continue
                if not foto_b64:
                    raise RuntimeError("não foi possível baixar uma imagem válida do produto")
                desconto = oferta.get("desconto", 0)
                frete = oferta.get("frete_gratis", False)
                badge = f'<span style="position:absolute;top:36px;right:36px;background:#e94560;color:#fff;font-size:64px;font-weight:800;padding:18px 36px;border-radius:20px;font-family:Segoe UI,sans-serif">-{desconto}%</span>' if desconto else ""
                frete_html = f'<div style="position:absolute;bottom:40px;left:40px;background:#1a7f3f;color:#fff;font-size:40px;font-weight:700;padding:14px 28px;border-radius:16px;font-family:Segoe UI,sans-serif">🚚 FRETE GRÁTIS</div>' if frete else ""
                html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:#fff}}.card{{width:1080px;height:1080px;position:relative;overflow:hidden;display:flex;align-items:center;justify-content:center}}img{{width:100%;height:100%;object-fit:contain;padding:60px}}</style></head><body><div class="card">{f'<img src="data:{foto_mime};base64,{foto_b64}">' if foto_b64 else '<div style="font-size:60px">📦</div>'}{badge}{frete_html}</div></body></html>"""
                page.set_content(html, wait_until="load")
                page.wait_for_timeout(300)
                path = os.path.join(DIVULGACAO, f"card_dia_{i+1:02d}.png")
                page.screenshot(path=path)
                cards.append(path)
                print(f"  ✅ Card {i+1}: {os.path.basename(path)}")
            except Exception as e:
                print(f"  ⚠️ Card {i+1} falhou: {e}")
                cards.append(None)
        browser.close()
    return cards

def carregar_cookies_portal():
    """Carrega os cookies do portal (salvos via Cookie-Editor) no formato Playwright."""
    import json as _json
    cookies_path = os.path.expanduser("~/.hermes/ml-affiliate/cookies_portal.json")
    if not os.path.exists(cookies_path):
        return []
    with open(cookies_path) as f:
        cookies = _json.load(f)
    pw = []
    for c in cookies:
        ss = c.get("sameSite") or "Lax"
        ss = {"no_restriction": "None", "lax": "Lax", "strict": "Strict"}.get(ss, "Lax")
        item = {"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c.get("path", "/"),
                "secure": c.get("secure", False), "httpOnly": c.get("httpOnly", False), "sameSite": ss}
        if c.get("expirationDate"):
            item["expires"] = c["expirationDate"]
        pw.append(item)
    return pw

def gerar_links_meli_batch(ofertas):
    """
    Gera links meli.la via API OFICIAL do portal (descoberta 13/08/2026).

    A interface nova (linkbuilder) chama:
      POST https://www.mercadolivre.com.br/affiliate-program/api/v2/affiliates/createLink
      Body: {"urls": [...], "tag": "renatoteodoro"}
    Retorna JSON com short_url (meli.la) por URL.

    Sessão: usa o perfil persistente do Chromium (chromium-data) — o navegador
    mantém a sessão de afiliado viva. NÃO injetar cookies do Cookie-Editor:
    cookies expirados SOBRESCREVEM a sessão boa do perfil e quebram o login.
    """
    USER_DATA_DIR = os.path.expanduser("~/.hermes/ml-affiliate/chromium-data")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            USER_DATA_DIR, headless=True, viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="pt-BR", args=["--disable-blink-features=AutomationControlled",
                                  "--disable-dev-shm-usage", "--no-sandbox",
                                  "--js-flags=--max-old-space-size=256"])
        page = ctx.new_page()
        page.goto("https://www.mercadolivre.com.br/afiliados/linkbuilder", timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(10000)

        # Verificar sessão: se redirecionou para login, a sessão do perfil caiu
        if "login" in page.url:
            print("  ❌ SESSÃO EXPIRADA: o portal redirecionou para login.")
            print("  ⚠️ Abra o linkbuilder no navegador do PC e faça login (a sessão salva no perfil).")
            ctx.close()
            return [None]*len(ofertas)

        links = [None]*len(ofertas)
        # ── SANITY CHECK: 1 URL primeiro para confirmar sessão viva ──
        # O que valida a sessão é a API RESPONDER (HTTP 200). O erro "URL not allowed"
        # (error_code 111) significa produto não autorizado — NÃO sessão morta.
        print("  🧪 Sanity check: testando sessão via API...")
        try:
            teste = page.evaluate("""async (urls) => {
                const r = await fetch('/affiliate-program/api/v2/affiliates/createLink', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({urls: urls, tag: 'renatoteodoro'})
                });
                return {status: r.status, data: await r.json()};
            }""", [ofertas[0]["link"]])
        except Exception as e:
            print(f"  ❌ SANITY CHECK FALHOU (fetch): {str(e)[:80]}")
            ctx.close()
            return [None]*len(ofertas)
        if teste.get("status") != 200:
            print(f"  ❌ SANITY CHECK FALHOU: HTTP {teste.get('status')} — sessão inválida (redirecionou p/ login?).")
            ctx.close()
            return [None]*len(ofertas)
        print("  ✅ Sanity check OK: API respondeu HTTP 200 — sessão viva, seguindo com o lote...")

        # ── LOTE: chamar a API com TODAS as URLs (em blocos de 10) ──
        # Bloco de 40 falhava silenciosamente (testado 13/08); 10 funciona 100%.
        print(f"  🔗 Gerando {len(ofertas)} links via API oficial...")
        TAM = 10
        for inicio in range(0, len(ofertas), TAM):
            fatia = ofertas[inicio:inicio+TAM]
            urls_bloco = [o["link"] for o in fatia]
            try:
                resp = page.evaluate("""async (urls) => {
                    const r = await fetch('/affiliate-program/api/v2/affiliates/createLink', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({urls: urls, tag: 'renatoteodoro'})
                    });
                    return {status: r.status, data: await r.json()};
                }""", urls_bloco)
            except Exception as e:
                print(f"  ⚠️ bloco {inicio//TAM+1} falhou: {str(e)[:80]}")
                continue
            if resp.get("status") != 200:
                print(f"  ⚠️ bloco {inicio//TAM+1}: HTTP {resp.get('status')} — pulando")
                continue
            for i, item in enumerate(resp.get("data", {}).get("urls", [])):
                if item.get("created") and item.get("short_url"):
                    links[inicio + i] = item["short_url"]
                else:
                    # Produto não autorizado no programa (error_code 111) — cai no fallback
                    pass
            ok_bloco = sum(1 for i in range(inicio, min(inicio+TAM, len(links))) if links[i])
            print(f"    ...{ok_bloco}/{len(fatia)} no bloco {inicio//TAM+1}")
            page.wait_for_timeout(1500)
        ctx.close()
        n_ok = sum(1 for l in links if l)
        print(f"  ✅ {n_ok}/{len(ofertas)} links meli.la gerados")
        if n_ok < len(ofertas):
            print(f"  ⚠️ {len(ofertas)-n_ok} produtos não autorizados no programa de afiliados — usarão link direto com tag")
        return links

async def bridge_estavel(min_estavel_seg=45):
    """
    Verifica se a bridge está estável (sem reconexão nos últimos `min_estavel_seg`).

    Contava "Connection closed" nas últimas 200 LINHAS do log, mas o bridge.log é
   竞技 movimentado por inbound/outbound: 200 linhas podem ser segundos de atividade
    ou meia hora de silêncio. Hoje isso prende o executor em ⏸️ até 3 min antes de
    CADA post, atrasando o dia inteiro — a bridge estava estável e o teste mentia.

    Agora mede TEMPO real: posição no arquivo (mtime/tamanho) + quantas quedas
    apareceram desde então. Estável = nenhuma queda nos últimos `min_estavel_seg`.
    """
    import subprocess as _sp
    log_path = os.path.expanduser("~/.hermes/whatsapp/bridge.log")
    try:
        # 1) Onde o log está agora (bytes) e quando foi escrito pela última vez.
        st = os.stat(log_path)
        pos_bytes = st.st_size
        parado_desde = time.time() - st.st_mtime

        # 2) Lê só a FATIA nova desde a última checagem: se ninguém reconectou
        #    recentemente e o log está quieto, a bridge está estável de fato.
        with open(log_path, "rb") as fh:
            fh.seek(max(0, pos_bytes - 65536))
            trecho = fh.read().decode("utf-8", errors="replace")
        quedas = trecho.count("Connection closed")

        # 3) Queda só conta se o log andou depois dela (senão é história antiga
        #    ainda dentro da janela de 64 KB) e se foi recente.
        if quedas == 0:
            return True
        # O log parou de escrever após a última queda = não reconectou desde então.
        if parado_desde >= min_estavel_seg:
            return True
        return False
    except Exception:
        return True  # em dúvida, permite (melhor que travar o roteiro)


# --- Circuit breaker + timeouts split (Correção 16/08 — GLM 5.3) ---
# GLOBAIS: persistem entre chamadas de enviar() — o breaker só funciona se o
# estado for compartilhado entre os posts (senão cada chamada reseta tudo).
_CB_FALHAS = 0
_CB_ABERTO_ATE = 0.0
_CB_LIMITE = 3        # falhas seguidas para abrir
_CB_ESPERA = 60.0     # segundos com breaker aberto
_TIMEOUT_CONEXAO = 10  # conexão
_TIMEOUT_LEITURA = 30  # leitura


async def enviar(chat, file_path, caption):
    """Envia card+caption ou só texto via bridge. SEMPRE retorna (status, msg), nunca lança exceção."""
    global _CB_FALHAS, _CB_ABERTO_ATE
    import urllib.request
    import http.client
    import random
    import socket

    class _Conn(http.client.HTTPConnection):
        def connect(self):
            super().connect()                       # conecta com timeout de CONEXÃO
            self.sock.settimeout(_TIMEOUT_LEITURA)  # timeout de LEITURA manual no socket

    class _Handler(urllib.request.HTTPHandler):
        def http_open(self, req):
            return self.do_open(_Conn, req)

    _opener = urllib.request.build_opener(_Handler)

    try:
        # --- Circuit breaker: se falhou 3x seguidas, espera 60s antes de tentar ---
        agora = time.monotonic()
        if _CB_FALHAS >= _CB_LIMITE:
            restante = _CB_ABERTO_ATE - agora
            if restante > 0:
                print(f"  ⛔ Circuit breaker ativo — aguardando {restante:.0f}s antes de tentar a bridge...")
                await asyncio.sleep(restante)
            _CB_FALHAS = 0

        if file_path and os.path.exists(file_path):
            payload = json.dumps({"chatId": chat, "filePath": file_path,
                                  "mediaType": "image", "caption": caption}).encode()
            req = urllib.request.Request(f"{BRIDGE}/send-media", data=payload,
                                         headers=bridge_headers())
        else:
            payload = json.dumps({"chatId": chat, "message": caption}).encode()
            req = urllib.request.Request(f"{BRIDGE}/send", data=payload,
                                         headers=bridge_headers())

        ultimo = (500, "nenhuma tentativa concluída")
        for tentativa in range(3):
            try:
                socket.setdefaulttimeout(_TIMEOUT_CONEXAO)  # timeout de CONEXÃO (10s)
                with _opener.open(req, timeout=_TIMEOUT_CONEXAO) as r:
                    status, msg = r.status, r.read().decode(errors="replace")[:100]
                _CB_FALHAS = 0  # sucesso zera falhas consecutivas
                return status, msg
            except Exception as e:
                ultimo = (getattr(e, "code", 500), str(e))
                print(f"  ⚠️ Tentativa {tentativa+1}/3 falhou: {str(e)[:80]}")
                if tentativa < 2:  # backoff exponencial + jitter: 1s, 2s, 4s
                    delay = (2 ** tentativa) + random.uniform(0, 0.3)
                    await asyncio.sleep(delay)

        # --- Falhou as 3 tentativas: alimenta o circuit breaker ---
        _CB_FALHAS += 1
        if _CB_FALHAS >= _CB_LIMITE:
            _CB_ABERTO_ATE = time.monotonic() + _CB_ESPERA
        return ultimo
    except Exception as e:
        return 500, str(e)

async def agendar_envios(posts, dry_run=False, forcar=None, revisar_apos=None):
    """Agenda e envia os posts nos horários exatos. revisar_apos=num do post p/ revisão automática."""
    agora = datetime.datetime.now()
    enviados = 0
    revisado = False
    for post in posts:
        hh, mm = map(int, post["horario"].split(":"))
        alvo = agora.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if forcar:
            fhh, fmm = map(int, forcar.split(":"))
            alvo = agora.replace(hour=fhh, minute=fmm, second=0, microsecond=0)
        if alvo <= agora and not forcar:
            # BOM DIA: somente às 08:00 da manhã, UMA ÚNICA VEZ por dia.
            # Se atrasou (relançamento pós-08:30 ou já enviado), PULA — nunca
            # reenvia fora do horário (15/08: watchdog relançou e spammou).
            if post.get("tipo") == "abertura" and post["num"] == 1:
                hh_atual = datetime.datetime.now().hour
                # Marcador COM DATA — expira naturalmente por dia (16/08: sem data,
                # o marcador de ontem pulava o bom dia de hoje indevidamente)
                marcador = f"/tmp/bom_dia_enviado_{datetime.datetime.now().strftime('%Y-%m-%d')}"
                ja_enviado = os.path.exists(marcador)
                if 8 <= hh_atual <= 10 and not ja_enviado:
                    print(f"  ⏰ Bom dia atrasado mas ainda de manhã — enviando (1ª e única vez)")
                    open(marcador, "w").write(datetime.datetime.now().isoformat())
                    espera = 0
                else:
                    print(f"  ⏭️ Post 1 (abertura) — bom dia fora do horário já enviado ou tarde demais, pulando")
                    continue
            else:
                print(f"  ⏭️ Post {post['num']} ({post['horario']}) — horário já passou, pulando")
                continue
        espera = (alvo - datetime.datetime.now()).total_seconds()
        if espera > 0 and not dry_run:
            print(f"  ⏳ Post {post['num']} ({post['horario']}): aguardando {espera/60:.1f} min...")
            await asyncio.sleep(espera)
        elif espera > 0 and dry_run:
            print(f"  ⏳ Post {post['num']} ({post['horario']}): aguardaria {espera/60:.1f} min (dry-run, sem esperar)")
        if dry_run:
            tipo = "TEXTO" if post["card"] is None else "CARD+TEXTO"
            print(f"  🧪 [DRY] Post {post['num']} {post['horario']} [{tipo}]: {post['texto'][:70]}...")
        else:
            # Esperar a bridge ESTABILIZAR antes de enviar (evita duplicação por reenvio pós-reconexão)
            for _tentativa in range(18):  # até 3 min
                if await bridge_estavel():
                    break
                print(f"  ⏸️ Bridge instável (reconexão recente) — aguardando estabilizar ({_tentativa+1}/18)...")
                await asyncio.sleep(10)
            status, resp = await enviar(GRUPO, post["card"], post["texto"])
            ok = "✅" if status == 200 else "❌"
            print(f"  {ok} Post {post['num']} ({post['horario']}): HTTP {status} {resp[:60]}")
            if status != 200:
                print(f"     texto: {post['texto'][:120]}")
        enviados += 1

        # REVISÃO AUTOMÁTICA após o primeiro post de oferta do dia
        if revisar_apos and not revisado and post["num"] == revisar_apos and not dry_run:
            revisado = True
            print(f"\n  🔍 REVISÃO pós-post {revisar_apos}...")
            try:
                json_path = os.path.expanduser(f"~/divulgacao/roteiro_{datetime.date.today().isoformat()}.json")
                r = subprocess.run([VENV_PY, os.path.join(REPO, "ml_revisao_post.py"), "--json", json_path, "--post", str(revisar_apos)],
                                   capture_output=True, text=True, timeout=150)
                saida = (r.stdout or "") + (r.stderr or "")
                print(f"  {saida[-600:]}")
                if r.returncode != 0:
                    print(f"  ⚠️ REVISÃO: problemas encontrados no Post {revisar_apos}!")
                else:
                    print(f"  ✅ REVISÃO OK: Post {revisar_apos} validado (card + link + texto)")
            except Exception as e:
                print(f"  ⚠️ Revisão falhou: {str(e)[:80]}")

    # Registrar links de afiliado e URLs canônicas no histórico anti-repetição.
    if not dry_run:
        links_postados = []
        links_canonicos = []
        for post in posts:
            if post.get("tipo") != "oferta":
                continue
            texto = post.get("texto", "")
            if "🔗 " in texto:
                link = texto.rsplit("🔗 ", 1)[-1].strip().splitlines()[0]
                if link:
                    links_postados.append(link)
            canonical = post.get("link_original")
            if canonical:
                links_canonicos.append(canonical)
        n = registrar_posts(links_postados, links_canonicos=links_canonicos)
        print(f"🗂️ {n} links de afiliado e {len(links_canonicos)} URLs de catálogo registrados no histórico")

    print(f"\n🏁 Concluído: {enviados} posts processados")

GLOBAL_LOCK_PATH = "/tmp/pipeline_global.lock"


def adquirir_lock():
    """Lock de instância única + lock GLOBAL compartilhado com o watchdog.

    Causa raiz das duplicações/perdas de 10/08: 3 execuções no mesmo dia (A/B/C)
    por relançamento manual. Com o flock, uma 2ª execução aborta na hora.
    Correção 16/08 (GLM 5.3): lock global em /tmp impede o watchdog de relançar
    enquanto o executor está vivo (corrida 08:30/08:35 de 16/08).
    """
    # ---------- 1) LOCK GLOBAL (compartilhado com o watchdog) ----------
    global_file = open(GLOBAL_LOCK_PATH, "a+")
    try:
        fcntl.flock(global_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("🚫 LOCK GLOBAL (/tmp/pipeline_global.lock) ocupado — o watchdog ou outro processo do pipeline está ativo. Abortando para evitar corrida de instâncias.")
        sys.exit(2)
    global_file.seek(0, os.SEEK_END)
    global_file.write(f"[GLOBAL] pid={os.getpid()} {datetime.datetime.now().isoformat()}\n")
    global_file.flush()

    # ---------- 2) LOCK LOCAL (existente) ----------
    lock_path = os.path.join(DIVULGACAO, "executor.lock")
    lock_file = open(lock_path, "a+")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("🚫 JÁ EXISTE um executor rodando (lock ativo). Abortando para evitar posts duplicados/perdidos.")
        print("   Se o relançamento for intencional, mate o processo anterior primeiro:")
        print("   pgrep -af ml_executor_diario  →  kill <PID>")
        try:
            fcntl.flock(global_file, fcntl.LOCK_UN)
        except OSError:
            pass
        global_file.close()
        sys.exit(2)
    lock_file.seek(0, os.SEEK_END)
    lock_file.write(f"{os.getpid()} {datetime.datetime.now().isoformat()}\n")
    lock_file.flush()

    return global_file, lock_file


def instancia_pipeline_ativa():
    """True se o lock global estiver ocupado (executor vivo) → NÃO relançar.
    Usado pelo WATCHDOG antes de matar/relançar."""
    probe = open(GLOBAL_LOCK_PATH, "a+")
    try:
        fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(probe, fcntl.LOCK_UN)
        probe.close()
        return False
    except OSError:
        probe.close()
        return True


def deduplicar_por_slug(ofertas):
    """
    Remove produtos duplicados do MESMO item do ML (mesmo slug de URL, anúncios diferentes).
    Mantém o de MAIOR desconto; empate → menor preço. (Correção 10/08, revisão GLM-5.2)
    """
    import re as _re
    def slug(link):
        if not isinstance(link, str) or not link:
            return ""
        try:
            from urllib.parse import urlsplit
            parts = urlsplit(link).path.strip("/").split("/")
            for i, part in enumerate(parts[:-1]):
                if part.lower() == "p" and parts[i + 1].upper().startswith("MLB"):
                    return "catalog:" + parts[i + 1].upper()
        except ValueError:
            pass
        m = _re.search(r"mercadolivre\.com\.br/([^/?]+)", link or "")
        return m.group(1) if m else (link or "")
    vistos = {}
    for o in ofertas:
        s = slug(o.get("link", ""))
        if not s:
            continue
        if s in vistos:
            atual = vistos[s]
            desc_atual = atual.get("desconto") or 0
            desc_novo = o.get("desconto") or 0
            # Manter maior desconto; empate → menor preço
            if desc_novo > desc_atual or (desc_novo == desc_atual and o.get("preco", 9e9) < atual.get("preco", 0)):
                vistos[s] = o
        else:
            vistos[s] = o
    return list(vistos.values())


def deduplicar_por_titulo(ofertas):
    """
    Segunda camada: mesmo produto com MLB IDs DIFERENTES (variações de cor/tamanho do mesmo item)
    têm títulos iguais. Remove duplicatas por título normalizado, mantendo maior desconto.
    (Correção 10/08 — caso Cadeira Gamer: cor branca vs cinza, MLB60051562 vs MLB64060677)
    """
    import re as _re
    def normalizar(t):
        t = (t or "").lower()
        t = _re.sub(r"[^a-z0-9 ]", " ", t)
        t = _re.sub(r"\s+", " ", t).strip()
        # Cortar em marcadores de variação (cor/tamanho/modelo) — mesmo produto, variação diferente
        for marcador in [" cor ", " tamanho ", " modelo ", " cor:", " cor "] + [" cor"]:
            idx = t.find(marcador)
            if 0 < idx < len(t) - 3:
                t = t[:idx]
                break
        return t.strip()
    vistos = {}
    for o in ofertas:
        n = normalizar(o.get("titulo", ""))
        if not n:
            continue
        if n in vistos:
            atual = vistos[n]
            desc_atual = atual.get("desconto") or 0
            desc_novo = o.get("desconto") or 0
            if desc_novo > desc_atual or (desc_novo == desc_atual and o.get("preco", 9e9) < atual.get("preco", 0)):
                vistos[n] = o
        else:
            vistos[n] = o
    return list(vistos.values())


def main():
    # ── CORREÇÃO 3 (GLM 5.3): log em APPEND com flush por linha — substitui o ">" do shell ──
    import io
    log_path = os.environ.get("ML_PROMO_LOG_PATH", f"/tmp/ml_exec_{datetime.date.today()}.log")
    try:
        raw = open(log_path, "ab", buffering=0)
        log_stream = io.TextIOWrapper(raw, encoding="utf-8", newline="\n",
                                      line_buffering=True, write_through=True)
        _stdout_original = sys.stdout
        sys.stdout = log_stream
        log_stream.write(f"\n===== REINÍCIO pid={os.getpid()} {datetime.datetime.now().isoformat()} | log={log_path} =====\n")
    except Exception:
        pass  # se não conseguir abrir o log, segue com stdout normal

    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Não envia, só mostra")
    ap.add_argument("--preparar", action="store_true", help="Gera ofertas, cards e links, sem enviar mensagens")
    ap.add_argument("--forcar-horario", default="", help="Envia tudo agora com este horário")
    ap.add_argument("--so-buscar", action="store_true", help="Só busca ofertas e salva JSON")
    ap.add_argument("--so-cards", action="store_true", help="Só gera cards (usa JSON salvo)")
    ap.add_argument("--so-links", action="store_true", help="Só gera links de afiliado (usa JSON salvo; não agenda envios)")
    ap.add_argument("--so-enviar", action="store_true", help="Só agenda/envia (usa JSON salvo)")
    args = ap.parse_args()

    # Lock de instância única — aborta se já houver executor rodando
    _global_lock, _lock_file = adquirir_lock()

    hoje = datetime.date.today().isoformat()
    try:
        os.makedirs(DIVULGACAO, exist_ok=True)
    except OSError as e:
        print(f"🚫 Não consegui abrir a pasta de divulgação: {type(e).__name__}: {e}")
        return 1
    json_path = os.path.join(DIVULGACAO, f"roteiro_{hoje}.json")

    # ── GUARDA ANTI-ROTEIRO-INCOMPLETO ──────────────────────────────────────
    # Envio e dry-run exigem o minimo configurado (ofertas, cards e links) afiliados.
    if args.so_enviar or args.dry_run or args.forcar_horario:
        if not os.path.exists(json_path):
            print("🚫 Roteiro de hoje NÃO existe — não há o que enviar.")
            return 1
        try:
            with open(json_path, encoding="utf-8") as f:
                _d = json.load(f)
            _ofertas = _d.get("ofertas") or []
            _cards = _d.get("cards") or []
            _links = _d.get("links") or []
            _n_cards = sum(1 for card in _cards if card and os.path.isfile(card))
            _n_afiliados = sum(1 for link in _links if link_afiliado_valido(link))
        except Exception as e:
            print(f"🚫 Roteiro inválido: {type(e).__name__}: {e}")
            return 1
        if len(_ofertas) < MIN_FLOOR or _n_cards < len(_ofertas) or _n_afiliados < len(_ofertas):
            print(f"🚫 Roteiro incompleto (ofertas={len(_ofertas)}, cards válidos={_n_cards}, "
                  f"links afiliados válidos={_n_afiliados}) — NÃO enviando.")
            print("   Regenerar com: python3 ml_executor_diario.py --preparar")
            return 1

    if args.so_enviar and args.preparar:
        print("🚫 Use apenas um entre --so-enviar e --preparar.")
        return 2

    # Fase 1: carregar um roteiro válido ou obter uma nova coleta.
    ofertas = []
    dados = {}
    precisa_buscar = args.so_buscar or not os.path.exists(json_path)
    somente_retomada = args.so_cards or args.so_links or args.so_enviar
    if somente_retomada and not os.path.exists(json_path):
        print("🚫 Não existe roteiro do dia para esta retomada; use --preparar primeiro.")
        return 1

    if os.path.exists(json_path) and not args.so_buscar:
        try:
            with open(json_path, encoding="utf-8") as f:
                dados = json.load(f)
            ofertas = dados.get("ofertas") or []
        except Exception as e:
            if somente_retomada:
                print(f"🚫 JSON do roteiro inválido: {type(e).__name__}: {e}")
                return 1
            print(f"⚠️ JSON do roteiro inválido; será feita nova coleta: {type(e).__name__}")
            precisa_buscar = True

        if len(ofertas) < MINIMO and len(ofertas) >= MIN_FLOOR:
            print(f"⚠️ Roteiro salvo enxuto ({len(ofertas)} ofertas) usando parcial (chao {MIN_FLOOR}).")
        elif len(ofertas) < MINIMO:
            if somente_retomada:
                print(f"🚫 Roteiro salvo tem apenas {len(ofertas)} ofertas; não vou completar com repetição.")
                print("   Gere um roteiro novo com: python3 ml_executor_diario.py --preparar")
                return 1
            print(f"⚠️ Roteiro salvo incompleto ({len(ofertas)} ofertas); descartando a coleta parcial e buscando de novo.")
            precisa_buscar = True
        elif not precisa_buscar:
            if not (dados.get("cards") or dados.get("links")):
                n_antes = len(ofertas)
                ofertas = deduplicar_por_slug(ofertas)
                ofertas = deduplicar_por_titulo(ofertas)
                if len(ofertas) < n_antes:
                    print(f"   🧹 Dedup no JSON parcial: {n_antes - len(ofertas)} duplicatas removidas")
                    dados["ofertas"] = ofertas
                    dados["cards"] = []
                    dados["links"] = []
            print(f"📂 Carregadas {len(ofertas)} ofertas do JSON de {hoje}")

    if precisa_buscar:
        print("🔍 Buscando ofertas do dia...")
        hist = carregar_historico()
        ja_postados = links_ja_postados_no_cooldown(
            hist.get("links", {}), cooldown_dias=REPETICAO_COOLDOWN_DIAS
        )
        from ml_api_source import published_catalog_ids
        ids_postados = published_catalog_ids(
            DIVULGACAO, ja_postados, cooldown_days=REPETICAO_COOLDOWN_DIAS
        )
        ja_postados.update(ids_postados)
        ofertas = buscar_98_ofertas(
            ja_postados=ja_postados, ids_postados=ids_postados,
            cooldown_days=REPETICAO_COOLDOWN_DIAS,
        )
        n_antes = len(ofertas)
        # Deduplicar antes da seleção para o limite de 140 não cair abaixo dele.
        ofertas = deduplicar_por_slug(ofertas)
        ofertas = deduplicar_por_titulo(ofertas)
        if len(ofertas) < n_antes:
            print(f"   🧹 Dedup: {n_antes - len(ofertas)} duplicatas do mesmo produto removidas")
        ofertas = selecionar_ofertas_com_natal(
            ofertas,
            n_desejado=MINIMO,
            ja_postados=ja_postados,
            data=hoje,
        )
        if len(ofertas) < MINIMO and len(ofertas) >= MIN_FLOOR:
            print(f"⚠️ Coleta enxuta: {len(ofertas)} ofertas (< {MINIMO}). Publicando as validas (grupo nunca fica sem ofertas).")
        elif len(ofertas) < MINIMO:
            print(f"🚫 Coleta encerrou com {len(ofertas)} ofertas unicas - abaixo do chao de {MIN_FLOOR}. Nenhuma postagem sera feita.")
            return 1
        print(f"✅ {len(ofertas)} ofertas selecionadas pela métrica")
        resumo = resumo_metrica(ofertas)
        print(f"   📊 Distribuição: R$20-50={resumo['micro_20_50']} | R$50-100={resumo['core_50_100']} | R$100-200={resumo['corep_100_200']} | R$200-500={resumo['medio_200_500']} | R$500-1000={resumo['oportunidade_500_1000']} | R$1000-3000={resumo['alto_1000_3000']} | R$3000-7000={resumo['premium_3000_7000']} | média R$ {resumo['preco_medio']}")

        # Dados vindos da API já têm preço do menor anúncio e desconto do mesmo vendedor.
        api_ofertas = [o for o in ofertas if str(o.get("fonte", "")).startswith("ml_api_")]
        site_ofertas = [o for o in ofertas if not str(o.get("fonte", "")).startswith("ml_api_")]
        if site_ofertas:
            print("🔎 Comparando preços de catálogo nas ofertas do site...")
            site_ofertas = enriquecer_lote(site_ofertas)
            print(f"   📊 Média após comparação do catálogo: R$ {resumo_metrica(site_ofertas)['preco_medio']}")
            print("🎟️ Verificando cupons apenas nas páginas de oferta acessíveis...")
            try:
                site_ofertas = detectar_cupons_lote(site_ofertas)
            except Exception as e:
                print(f"   ⚠️ Detecção de cupons falhou: {str(e)[:80]} (seguindo sem cupons)")
        ofertas = site_ofertas + api_ofertas
        dados = {"data": hoje, "ofertas": ofertas, "cards": [], "links": []}
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1)

    if args.so_buscar:
        print(f"✅ Busca concluída: {len(ofertas)} ofertas salvas em {json_path}; nenhuma mensagem enviada.")
        return 0
    if len(ofertas) < MINIMO and len(ofertas) >= MIN_FLOOR:
        print(f"⚠️ Coleta enxuta ({len(ofertas)} ofertas): montando roteiro parcial (grupo nunca fica sem ofertas).")
    elif len(ofertas) < MINIMO:
        print(f"🚫 Só há {len(ofertas)} ofertas únicas (abaixo do chao de {MIN_FLOOR}); o roteiro não será montado nem enviado.")
        return 1

    # Fase 2: cards. Só aceita imagens realmente baixadas e arquivos existentes.
    cards = dados.get("cards") or []
    cards_validos = sum(1 for card in cards if card and os.path.isfile(card))
    if cards_validos < max(MIN_FLOOR, len(ofertas)) and not args.so_links and not args.so_enviar:
        print(f"🖼️ Gerando cards (válidos no JSON: {cards_validos}/140)...")
        try:
            cards = gerar_cards_batch(ofertas)
        except Exception as e:
            print(f"🚫 Não consegui abrir o gerador de cards: {type(e).__name__}: {str(e)[:120]}")
            cards = [None] * len(ofertas)
        dados["ofertas"] = ofertas
        dados["cards"] = cards
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1)
        cards_validos = sum(1 for card in cards if card and os.path.isfile(card))
    if args.so_cards:
        print(f"✅ Geração de cards concluída: {cards_validos}/140 arquivos válidos; nenhuma mensagem enviada.")
        return 0 if cards_validos >= 140 else 1
    if not args.so_links and cards_validos < max(MIN_FLOOR, len(ofertas)):
        print(f"🚫 Apenas {cards_validos}/140 cards válidos; não vou gerar um roteiro enviável.")
        return 1

    # Fase 3: links oficiais meli.la; se necessário, fallback direto com tag.
    links = dados.get("links") or []
    links_validos = sum(1 for link in links if link_afiliado_valido(link))
    if links_validos < 140 and not args.so_enviar:
        print(f"🔗 Gerando links de afiliado (válidos no JSON: {links_validos}/140)...")
        try:
            novos_links = gerar_links_meli_batch(ofertas)
        except Exception as e:
            print(f"  ⚠️ Portal de afiliados indisponível ({type(e).__name__}: {str(e)[:100]}); usando fallback direto com tag.")
            novos_links = [None] * len(ofertas)
        links = list(links)
        while len(links) < len(ofertas):
            links.append(None)
        for i, oferta in enumerate(ofertas):
            if link_afiliado_valido(links[i]):
                continue
            candidato = novos_links[i] if i < len(novos_links) else None
            if link_afiliado_valido(candidato):
                links[i] = candidato
            else:
                links[i] = link_direto_afiliado(oferta.get("link", "")) or None
        dados["links"] = links
        dados["ofertas"] = ofertas
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1)
        n_meli = sum(1 for link in links if isinstance(link, str) and "meli.la/" in link)
        links_validos = sum(1 for link in links if link_afiliado_valido(link))
        print(f"   ✅ {links_validos}/{MINIMO} links afiliados válidos ({n_meli} meli.la; restante com tag direta)")

    if args.so_links:
        print(f"✅ Geração de links concluída: {links_validos}/{MINIMO} válidos; nenhuma mensagem enviada.")
        return 0 if links_validos >= MINIMO else 1
    if links_validos < max(MIN_FLOOR, len(ofertas)):
        print(f"🚫 Apenas {links_validos}/{MINIMO} links afiliados válidos; envio bloqueado.")
        return 1

    dados["cards"] = cards
    dados["links"] = links
    dados["ofertas"] = ofertas
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)

    if args.preparar:
        print(f"✅ Roteiro preparado sem enviar mensagens: {len(ofertas)} ofertas, {cards_validos} cards e {links_validos} links afiliados.")
        return 0

    # FASE 3.5: VALIDAR links x ofertas (og:title) — incidente 11/08 (links deslocados +1)
    # O gerador pode associar meli.la ao produto errado (DOM da página); corrige antes de postar.
    #
    # TIMEOUT (02/10): abrir o Chromium e percorrer ~140 links meli.la consome mais
    # que 2h com o portal lento de IP de VPS, e esse era o ÚNICO passo do fluxo
    # completo que roda ANTES de qualquer envio. Estourava o TimeoutStopSec=7200 do
    # promo-pipeline.service às 09:00 em 8 dias seguidos, matando o gerador das 07:00
    # antes de o dia começar.
    #
    # Com o minimo configurado (ofertas, cards e links) afiliados válidos, a
    # validação de página é redundante e falha por bloqueio anti-bot da VPS.
    roteiro_completo = (
        len(ofertas) >= 140
        and cards_validos >= 140
        and links_validos >= 140
    )
    if not args.so_enviar and not args.dry_run and not roteiro_completo:
        try:
            from ml_validar_links import validar_links
            _ok, _corr, _sem = validar_links(json_path)
            if _corr:
                print(f"🔎 {_corr} links corrigidos para link direto com tag (validados por og:title)")
            with open(json_path) as f:
                dados = json.load(f)
            links = dados.get("links") or []
        except Exception as e:
            print(f"⚠️ Validação de links falhou: {str(e)[:80]} (seguindo com links atuais)")

    # Vincular links às ofertas
    for i, o in enumerate(ofertas):
        if i < len(links) and links[i]:
            o["link_meli"] = links[i]
        else:
            o["link_meli"] = None

    # Fase 4: construir roteiro e agendar
    dia_idx = hoje.replace("-", "")[-2:]
    try:
        dia_idx = int(dia_idx) % 7
    except:
        dia_idx = 0
    chamadas = dados.get("chamadas") or None
    posts = construir_roteiro(ofertas, hoje, dia_idx, cards=cards, links=links, chamadas=chamadas)
    print(f"📋 Roteiro montado: {len(posts)} posts ({hoje})")

    # Sanidade: verificar os 3 primeiros posts de oferta (card + link + chamada)
    for p in posts[1:4]:
        tem_card = "✅" if p["card"] and os.path.exists(p["card"]) else "❌"
        link_ok = "meli.la" in p["texto"] if "meli.la" in p["texto"] else "⚠️ link completo"
        eco_ok = "ECONOMIZE" in p["texto"] if "ECONOMIZE" in p["texto"] else "⚠️ sem economia"
        print(f"  Post {p['num']}: card {tem_card} | {link_ok} | {eco_ok}")

    # REVISÃO AUTOMÁTICA após o primeiro post de oferta (Post 2, 08:05)
    # Verifica: card correto (visão Luna) + link meli.la + texto coerente
    revisar = None if args.so_enviar else 2
    asyncio.run(agendar_envios(posts, dry_run=args.dry_run, forcar=args.forcar_horario, revisar_apos=revisar))

if __name__ == "__main__":
    sys.exit(main())
