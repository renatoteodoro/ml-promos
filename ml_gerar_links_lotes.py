#!/usr/bin/env python3
"""Gera links meli.la em LOTES de 20 (testado e funcionando), salvando incrementalmente no JSON.
Uso: python3 ml_gerar_links_lotes.py
"""
import os, sys, time, json, re, datetime

SHOT_DIR = os.path.expanduser("~/.hermes/ml-affiliate")
# Data alvo: argumento --data=YYYY-MM-DD ou hoje por padrão (corrigido 11/08: era hardcoded 10/08)
_data_arg = None
for a in sys.argv[1:]:
    if a.startswith("--data="):
        _data_arg = a.split("=", 1)[1]
_data = _data_arg or datetime.date.today().isoformat()
JSON_PATH = os.path.expanduser(f"~/divulgacao/roteiro_{_data}.json")
USER_DATA_DIR = os.path.expanduser("~/.hermes/ml-affiliate/chromium-data")
COOKIES_PATH = os.path.expanduser("~/.hermes/ml-affiliate/cookies_portal.json")

def carregar_cookies():
    """Carrega cookies do portal (Cookie-Editor) no formato Playwright."""
    if not os.path.exists(COOKIES_PATH):
        return []
    with open(COOKIES_PATH) as f:
        cookies = json.load(f)
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

def get_browser(p):
    return p.chromium.launch_persistent_context(
        USER_DATA_DIR,
        headless=True,
        viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="pt-BR",
        args=["--disable-blink-features=AutomationControlled"],
    )

def extrair_links(page, n_esperados):
    vals = page.eval_on_selector_all("input, textarea", "els => els.map(e => e.value || e.textContent).filter(v => v && v.includes('meli.la'))")
    texts_all = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0).map(e => e.textContent).filter(t => t && t.includes('meli.la'))")
    hrefs = page.eval_on_selector_all("a", "els => els.map(e => e.href).filter(h => h && h.includes('meli.la'))")
    todos = vals + texts_all + hrefs
    links, vistos = [], set()
    for v in todos:
        for m in re.findall(r'https?://meli\.la/\w+', v):
            if m not in vistos:
                vistos.add(m)
                links.append(m)
    return links

def main():
    with open(JSON_PATH) as f:
        dados = json.load(f)
    ofertas = dados["ofertas"]
    links_existentes = dados.get("links") or []
    print(f"Ofertas: {len(ofertas)} | Links já gerados: {len(links_existentes)}")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = get_browser(p)
        page = ctx.new_page()
        # INJETAR COOKIES DO PORTAL (sessão Cookie-Editor)
        cookies = carregar_cookies()
        if cookies:
            page.goto("https://www.mercadolivre.com.br", timeout=30000, wait_until="domcontentloaded")
            ctx.add_cookies(cookies)
            print(f"🔐 {len(cookies)} cookies injetados")
        # Abrir o gerador UMA vez
        page.goto("https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true", timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(10000)
        el = page.query_selector("text=Gerador de links")
        if el:
            el.click(force=True)
            page.wait_for_timeout(8000)

        ta = page.query_selector("textarea:visible")
        if not ta:
            print("❌ textarea não encontrado")
            ctx.close()
            return

        # Processar em lotes de 20
        TAM = 20
        for inicio in range(0, len(ofertas), TAM):
            fatia = ofertas[inicio:inicio+TAM]
            lote_atual = links_existentes[inicio:inicio+TAM]
            # Só pular se os links do lote já forem meli.la (não links diretos de fallback)
            if lote_atual and all(l and "meli.la" in l for l in lote_atual):
                print(f"⏭️ Lote {inicio//TAM + 1} já tem meli.la, pulando")
                continue
            urls = "\n".join(o["link"] for o in fatia)
            ta.fill(urls)
            page.wait_for_timeout(1500)
            btn = page.query_selector("button:has-text('Gerar')")
            if btn:
                btn.click(force=True)
                print(f"🔗 Lote {inicio//TAM + 1} ({(inicio+1)}-{inicio+len(fatia)}): gerando {len(fatia)} links...")
                links = []
                for _ in range(8):  # até 4 min
                    page.wait_for_timeout(25000)
                    links = extrair_links(page, len(fatia))
                    print(f"    ...{len(links)} links")
                    if len(links) >= len(fatia):
                        break
                if len(links) >= len(fatia):
                    # Preencher a partir do início do lote
                    for j, l in enumerate(links[:len(fatia)]):
                        idx = inicio + j
                        while len(links_existentes) <= idx:
                            links_existentes.append(None)
                        links_existentes[idx] = l
                    dados["links"] = links_existentes
                    with open(JSON_PATH, "w") as f:
                        json.dump(dados, f, ensure_ascii=False, indent=1)
                    print(f"    ✅ Lote salvo ({len(links)} links)")
                else:
                    # SALVAR PARCIAL: mesmo incompleto, aproveita os links gerados (fix 11/08)
                    print(f"    ⚠️ Lote {inicio//TAM + 1} incompleto ({len(links)}/{len(fatia)}) — salvando parcial")
                    for j, l in enumerate(links):
                        idx = inicio + j
                        while len(links_existentes) <= idx:
                            links_existentes.append(None)
                        links_existentes[idx] = l
                    dados["links"] = links_existentes
                    with open(JSON_PATH, "w") as f:
                        json.dump(dados, f, ensure_ascii=False, indent=1)
                page.wait_for_timeout(3000)
        ctx.close()

    # Relatório final
    with open(JSON_PATH) as f:
        dados = json.load(f)
    links = dados.get("links") or []
    validos = sum(1 for l in links if l)
    print(f"\n🏁 Links gerados: {validos}/{len(dados['ofertas'])}")

if __name__ == "__main__":
    main()
