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

REPO = os.path.expanduser("~/ml-promos-repo")
VENV_PY = os.path.expanduser("~/.hermes/hermes-agent/venv/bin/python3")
DIVULGACAO = os.path.expanduser("~/divulgacao")
GRUPO = "120363428591609827@g.us"
BRIDGE = "http://127.0.0.1:3000"

sys.path.insert(0, REPO)
from ml_promo import extrair_ofertas_html
from ml_roteiro_diario import HORARIOS, construir_roteiro
from ml_metrica import filtrar_por_metrica, carregar_historico, registrar_posts, resumo_metrica
from ml_compare_preco import enriquecer_lote
from ml_detectar_cupons import processar as detectar_cupons_lote

def buscar_98_ofertas():
    """Busca ofertas únicas paginando /ofertas até 102+ (14 páginas p/ ter variedade de preço)."""
    todas, links_vistos = [], set()
    for pg in range(1, 15):
        try:
            ofs = extrair_ofertas_html(f"https://www.mercadolivre.com.br/ofertas?page={pg}")
        except Exception as e:
            print(f"  ⚠️ Página {pg}: {e}")
            break
        novas = [o for o in ofs if o["link"] not in links_vistos]
        for o in novas:
            links_vistos.add(o["link"])
        todas.extend(novas)
        print(f"  Página {pg}: +{len(novas)} (total {len(todas)})")
        if len(todas) >= 300:
            break
        time.sleep(0.5)
    return todas

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
                # Baixar foto
                foto_url = oferta.get("imagem", "")
                foto_b64 = ""
                if foto_url:
                    req = urllib.request.Request(foto_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=15) as r:
                        foto_b64 = base64.b64encode(r.read()).decode()
                desconto = oferta.get("desconto", 0)
                frete = oferta.get("frete_gratis", False)
                badge = f'<span style="position:absolute;top:36px;right:36px;background:#e94560;color:#fff;font-size:64px;font-weight:800;padding:18px 36px;border-radius:20px;font-family:Segoe UI,sans-serif">-{desconto}%</span>' if desconto else ""
                frete_html = f'<div style="position:absolute;bottom:40px;left:40px;background:#1a7f3f;color:#fff;font-size:40px;font-weight:700;padding:14px 28px;border-radius:16px;font-family:Segoe UI,sans-serif">🚚 FRETE GRÁTIS</div>' if frete else ""
                html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:#fff}}.card{{width:1080px;height:1080px;position:relative;overflow:hidden;display:flex;align-items:center;justify-content:center}}img{{width:100%;height:100%;object-fit:contain;padding:60px}}</style></head><body><div class="card">{f'<img src="data:image/png;base64,{foto_b64}">' if foto_b64 else '<div style="font-size:60px">📦</div>'}{badge}{frete_html}</div></body></html>"""
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

async def bridge_estavel(min_estavel_seg=60):
    """
    Verifica se a bridge está estável (sem reconexões nos últimos N segundos).
    Retorna True se estável. Evita envio durante reconexão (causa de duplicação:
    o Baileys reenvia mensagens pendentes após reconectar → WhatsApp entrega 2x).
    """
    import subprocess as _sp
    try:
        r = _sp.run(["tail", "-200", os.path.expanduser("~/.hermes/whatsapp/bridge.log")],
                    capture_output=True, text=True, timeout=10)
        log = r.stdout
        if "Connection closed" not in log:
            return True
        # Achar o timestamp da última reconexão no log
        import re as _re
        # Log tem timestamps? Se não, contar ocorrências recentes (últimas 200 linhas)
        quedas = log.count("Connection closed")
        # Bridge loga em tempo real — 200 linhas ≈ últimos minutos
        # Se mais de 2 quedas nas últimas 200 linhas, provavelmente instável
        if quedas > 2:
            return False
        return True
    except Exception:
        return True  # em dúvida, permite (melhor que travar o roteiro)


async def enviar(chat, file_path, caption):
    """Envia card+caption ou só texto via bridge."""
    import urllib.request
    if file_path and os.path.exists(file_path):
        payload = json.dumps({"chatId": chat, "filePath": file_path, "mediaType": "image", "caption": caption}).encode()
        req = urllib.request.Request(f"{BRIDGE}/send-media", data=payload, headers={"Content-Type": "application/json"})
    else:
        payload = json.dumps({"chatId": chat, "message": caption}).encode()
        req = urllib.request.Request(f"{BRIDGE}/send", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode()[:100]
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
                marcador = "/tmp/bom_dia_enviado_hoje"
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

    # Registrar links postados no histórico (anti-repetição para amanhã)
    if not dry_run:
        links_postados = [p.get("texto", "").split("🔗 ")[-1].strip() for p in posts if p.get("tipo") == "oferta" and "🔗 " in p.get("texto", "")]
        n = registrar_posts(links_postados)
        print(f"🗂️ {n} links registrados no histórico (anti-repetição)")

    print(f"\n🏁 Concluído: {enviados} posts processados")

def adquirir_lock():
    """Lock de instância única (fcntl flock) — impede 2 executores no mesmo dia.

    Causa raiz das duplicações/perdas de 10/08: 3 execuções no mesmo dia (A/B/C)
    por relançamento manual. Com o flock, uma 2ª execução aborta na hora.
    """
    lock_path = os.path.join(DIVULGACAO, "executor.lock")
    lock_file = open(lock_path, "a+")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("🚫 JÁ EXISTE um executor rodando (lock ativo). Abortando para evitar posts duplicados/perdidos.")
        print("   Se o relançamento for intencional, mate o processo anterior primeiro:")
        print("   pgrep -af ml_executor_diario  →  kill <PID>")
        sys.exit(2)
    lock_file.write(f"{os.getpid()} {datetime.datetime.now().isoformat()}\n")
    lock_file.flush()
    return lock_file


def deduplicar_por_slug(ofertas):
    """
    Remove produtos duplicados do MESMO item do ML (mesmo slug de URL, anúncios diferentes).
    Mantém o de MAIOR desconto; empate → menor preço. (Correção 10/08, revisão GLM-5.2)
    """
    import re as _re
    def slug(link):
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Não envia, só mostra")
    ap.add_argument("--forcar-horario", default="", help="Envia tudo agora com este horário")
    ap.add_argument("--so-buscar", action="store_true", help="Só busca ofertas e salva JSON")
    ap.add_argument("--so-cards", action="store_true", help="Só gera cards (usa JSON salvo)")
    ap.add_argument("--so-links", action="store_true", help="Só gera links meli.la (usa JSON salvo)")
    ap.add_argument("--so-enviar", action="store_true", help="Só agenda/envia (usa JSON salvo)")
    args = ap.parse_args()

    # Lock de instância única — aborta se já houver executor rodando
    _lock_file = adquirir_lock()

    hoje = datetime.date.today().isoformat()
    json_path = os.path.join(DIVULGACAO, f"roteiro_{hoje}.json")

    # ── GUARDA ANTI-ROTEIRO-INCOMPLETO ──────────────────────────────────────
    # Se for --so-enviar (ou --dry-run/--forcar-horario que também enviam) e o
    # roteiro existir mas estiver INCOMPLETO (cards/links ausentes — geração
    # abortada), NÃO envia: posts sairiam sem imagem e sem link meli.la.
    if args.so_enviar or args.dry_run or args.forcar_horario:
        if os.path.exists(json_path):
            try:
                with open(json_path) as f:
                    _d = json.load(f)
                _cards = _d.get("cards") or []
                _links = _d.get("links") or []
                _n_meli = sum(1 for l in _links if l and "meli.la" in l)
                if len(_cards) < 100 or _n_meli < 100:
                    print(f"🚫 Roteiro de hoje INCOMPLETO (cards={len(_cards)}, "
                          f"meli.la={_n_meli}) — NÃO enviando para não postar sem "
                          f"imagem/link encurtado.")
                    print("   Regenerar: python3 ml_executor_diario.py --so-links")
                    return 1
            except Exception:
                pass
        else:
            print("🚫 Roteiro de hoje NÃO existe — não há o que enviar.")
            return 1

    if args.so_buscar or (not args.so_cards and not args.so_links and not args.so_enviar and not args.dry_run and not args.forcar_horario):
        pass  # fluxo completo
    elif args.so_buscar:
        pass

    # Fase 1: buscar ofertas (se não tiver JSON ou for fluxo completo)
    ofertas = []
    if os.path.exists(json_path) and not args.so_buscar:
        with open(json_path) as f:
            dados = json.load(f)
        ofertas = dados.get("ofertas", [])
        # DEDUP dupla camada também no JSON salvo (retomada do fluxo)
        n_antes = len(ofertas)
        ofertas = deduplicar_por_slug(ofertas)
        ofertas = deduplicar_por_titulo(ofertas)
        if len(ofertas) < n_antes:
            print(f"   🧹 Dedup no JSON: {n_antes - len(ofertas)} duplicatas removidas")
        print(f"📂 Carregadas {len(ofertas)} ofertas do JSON de {hoje}")
    else:
        print("🔍 Buscando ofertas do dia...")
        ofertas = buscar_98_ofertas()
        # Aplicar MÉTRICA de preço + anti-repetição (definida 08/08)
        hist = carregar_historico()
        ja_postados = set(hist.get("links", {}).keys())
        ofertas = filtrar_por_metrica(ofertas, n_desejado=140, ja_postados=ja_postados)
        # DEDUP dupla camada (GLM-5.2 10/08): slug (mesmo item) + título (variações do mesmo produto)
        n_antes = len(ofertas)
        ofertas = deduplicar_por_slug(ofertas)
        ofertas = deduplicar_por_titulo(ofertas)
        if len(ofertas) < n_antes:
            print(f"   🧹 Dedup: {n_antes - len(ofertas)} duplicatas do mesmo produto removidas")
        print(f"✅ {len(ofertas)} ofertas selecionadas pela métrica")
        resumo = resumo_metrica(ofertas)
        print(f"   📊 Distribuição: R$20-50={resumo['micro_20_50']} | R$50-100={resumo['core_50_100']} | R$100-200={resumo['corep_100_200']} | R$200-500={resumo['medio_200_500']} | R$500-1000={resumo['oportunidade_500_1000']} | R$1000-3000={resumo['alto_1000_3000']} | R$3000-7000={resumo['premium_3000_7000']} | média R$ {resumo['preco_medio']}")
        # Comparação de preços: buscar MENOR preço do catálogo (vários vendedores)
        print("🔎 Comparando preços entre vendedores do mesmo produto (catálogo)...")
        ofertas = enriquecer_lote(ofertas)
        resumo2 = resumo_metrica(ofertas)
        print(f"   📊 Após comparação: média R$ {resumo2['preco_medio']} | R$20-50={resumo2['micro_20_50']} | R$50-100={resumo2['core_50_100']} | R$100-200={resumo2['corep_100_200']} | R$200-500={resumo2['medio_200_500']}")
        # Detectar cupons ativos nos produtos (ex: "X% OFF com Cupom")
        print("🎟️ Verificando cupons ativos nos produtos...")
        try:
            ofertas = detectar_cupons_lote(ofertas)
        except Exception as e:
            print(f"   ⚠️ Detecção de cupons falhou: {str(e)[:80]} (seguindo sem cupons)")
        with open(json_path, "w") as f:
            json.dump({"data": hoje, "ofertas": ofertas, "cards": [], "links": []}, f, ensure_ascii=False, indent=1)

    if len(ofertas) < 140:
        print(f"⚠️ Só {len(ofertas)} ofertas — roteiro poderá usar repetição")

    # Fase 2: cards (se não existirem)
    with open(json_path) as f:
        dados = json.load(f)
    cards = dados.get("cards") or []
    if len(cards) < 140 and not args.so_links and not args.so_enviar:
        print("🖼️ Gerando cards...")
        cards = gerar_cards_batch(ofertas)
        dados["cards"] = cards
        with open(json_path, "w") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1)

    # Fase 3: links meli.la (se não existirem)
    links = dados.get("links") or []
    if len(links) < 140 and not args.so_enviar:
        print("🔗 Gerando links meli.la...")
        links = gerar_links_meli_batch(ofertas)
        # FALLBACK ANTI-INTERRUPÇÃO: se o portal falhar (sessão expirada/captcha),
        # usar link direto com tag de afiliado (formato oficial, rastreia igual)
        if len(links) < 140:
            print(f"⚠️ Só {len(links)} meli.la gerados — completando com links diretos com tag...")
            for i, o in enumerate(ofertas):
                if i < len(links) and links[i]:
                    continue
                # Extrair MLB id do link original (aceita /p/MLB e formato de anúncio MLB-XXXXXXXXX-)
                m = re.search(r"/p/(MLB\d+)", o.get("link", "")) or re.search(r"(MLB-\d{7,})", o.get("link", "")) or re.search(r"(MLB\d{7,})", o.get("link", ""))
                if m:
                    mlb_id = m.group(1).replace("-", "")
                    link_tag = f"https://www.mercadolivre.com.br/p/{mlb_id}?matt_word=renatoteodoro&matt_tool=94885465"
                    while len(links) <= i:
                        links.append(None)
                    links[i] = link_tag
                else:
                    while len(links) <= i:
                        links.append(None)
                    links[i] = o.get("link", "")
        dados["links"] = links
        with open(json_path, "w") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1)
        n_meli = sum(1 for l in links if l and "meli.la" in l)
        print(f"   ✅ {len(links)} links prontos ({n_meli} meli.la + {len(links)-n_meli} diretos com tag)")

    # FASE 3.5: VALIDAR links x ofertas (og:title) — incidente 11/08 (links deslocados +1)
    # O gerador pode associar meli.la ao produto errado (DOM da página); corrige antes de postar.
    if not args.so_enviar and not args.dry_run:
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
    main()
