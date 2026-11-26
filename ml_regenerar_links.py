#!/usr/bin/env python3
"""Regenera links meli.la para índices específicos que ficaram como link direto."""
import os, sys, json, time, re

REPO = os.path.expanduser("~/ml-promos-repo")
sys.path.insert(0, REPO)

JSON_PATH = os.path.expanduser("~/divulgacao/roteiro_2026-08-10.json")
USER_DATA_DIR = os.path.expanduser("~/.hermes/ml-affiliate/chromium-data")
COOKIES_PATH = os.path.expanduser("~/.hermes/ml-affiliate/cookies_portal.json")

def carregar_cookies():
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

def main():
    from playwright.sync_api import sync_playwright

    with open(JSON_PATH) as f:
        dados = json.load(f)
    ofertas = dados["ofertas"]
    links = dados.get("links") or []

    # Índices que precisam de meli.la (diretos)
    indices = [i for i, l in enumerate(links) if l and "meli.la" not in l]
    if not indices:
        print("✅ Nenhum link direto — tudo meli.la!")
        return
    print(f"Regenerando {len(indices)} links (índices {indices[0]}-{indices[-1]})")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            USER_DATA_DIR, headless=True, viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="pt-BR", args=["--disable-blink-features=AutomationControlled"])
        page = ctx.new_page()
        cookies = carregar_cookies()
        if cookies:
            page.goto("https://www.mercadolivre.com.br", timeout=30000, wait_until="domcontentloaded")
            ctx.add_cookies(cookies)
            print(f"🔐 {len(cookies)} cookies injetados")

        page.goto("https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true", timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(10000)
        el = page.query_selector("text=Gerador de links")
        if el:
            el.click(force=True)
            page.wait_for_timeout(8000)

        # Processar em lotes de 20 (os 20 diretos)
        for inicio in range(0, len(indices), 20):
            fatia_idx = indices[inicio:inicio+20]
            urls = "\n".join(ofertas[i]["link"] for i in fatia_idx)
            ta = page.query_selector("textarea:visible")
            if not ta:
                print("❌ textarea não encontrado")
                break
            ta.fill(urls)
            page.wait_for_timeout(1500)
            btn = page.query_selector("button:has-text('Gerar')")
            if not btn:
                print("❌ Botão Gerar não encontrado")
                break
            btn.click(force=True)
            print(f"🔗 Gerando {len(fatia_idx)} links...")
            links_encontrados = []
            for _ in range(10):
                page.wait_for_timeout(25000)
                vals = page.eval_on_selector_all("input, textarea", "els => els.map(e => e.value || e.textContent).filter(v => v && v.includes('meli.la'))")
                texts_all = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0).map(e => e.textContent).filter(t => t && t.includes('meli.la'))")
                todos = vals + texts_all
                links_encontrados = []
                vistos = set()
                for v in todos:
                    for m in re.findall(r'https?://meli\.la/\w+', v):
                        if m not in vistos:
                            vistos.add(m)
                            links_encontrados.append(m)
                print(f"    ...{len(links_encontrados)}/{len(fatia_idx)} links")
                if len(links_encontrados) >= len(fatia_idx):
                    break
            # Salvar
            for j, idx in enumerate(fatia_idx):
                if j < len(links_encontrados):
                    links[idx] = links_encontrados[j]
            dados["links"] = links
            with open(JSON_PATH, "w") as f:
                json.dump(dados, f, ensure_ascii=False, indent=1)
            print(f"✅ Lote salvo ({sum(1 for l in links if l and 'meli.la' in l)}/{len(links)} meli.la)")

        ctx.close()

    # Resumo
    n_meli = sum(1 for l in links if l and "meli.la" in l)
    print(f"\n🏁 Final: {n_meli}/{len(links)} meli.la | {len(links)-n_meli} diretos")

if __name__ == "__main__":
    main()
