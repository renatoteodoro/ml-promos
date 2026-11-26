#!/usr/bin/env python3
"""Teste FINAL: Gerador de Links com URL de cupom + produto (com cookies injetados)."""
import os, sys, json, time, re

USER_DATA_DIR = os.path.expanduser("~/.hermes/ml-affiliate/chromium-data")
COOKIES_PATH = os.path.expanduser("~/.hermes/ml-affiliate/cookies_portal.json")
SHOT_DIR = os.path.expanduser("~/.hermes/ml-affiliate")

def get_browser(p):
    return p.chromium.launch_persistent_context(
        USER_DATA_DIR,
        headless=True,
        viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="pt-BR",
        args=["--disable-blink-features=AutomationControlled"],
    )

def main():
    from playwright.sync_api import sync_playwright

    with open(COOKIES_PATH) as f:
        cookies = json.load(f)
    pw_cookies = []
    for c in cookies:
        ss = c.get("sameSite") or "Lax"
        ss = {"no_restriction": "None", "lax": "Lax", "strict": "Strict"}.get(ss, "Lax")
        pw = {"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c.get("path", "/"),
              "secure": c.get("secure", False), "httpOnly": c.get("httpOnly", False), "sameSite": ss}
        if c.get("expirationDate"):
            pw["expires"] = c["expirationDate"]
        pw_cookies.append(pw)

    with sync_playwright() as p:
        ctx = get_browser(p)
        page = ctx.new_page()
        try:
            page.goto("https://www.mercadolivre.com.br", timeout=30000, wait_until="domcontentloaded")
            ctx.add_cookies(pw_cookies)

            # Abrir o Gerador de Links (clique direto no elemento)
            page.goto("https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(8000)
            el = page.query_selector("text=Gerador de links")
            if el:
                el.click(force=True)
                print("Clicou em 'Gerador de links'")
            else:
                print("⚠️ 'Gerador de links' não encontrado como texto")
            page.wait_for_timeout(10000)
            print(f"URL gerador: {page.url[:80]}")
            page.screenshot(path=os.path.join(SHOT_DIR, "gerador_cookies.png"))

            # Colar 2 URLs: um produto e a página de cupons
            ta = page.query_selector("textarea:visible")
            if not ta:
                print("❌ textarea não encontrado")
                # Listar inputs visíveis
                inputs = page.eval_on_selector_all("textarea, input", "els => els.map(e => e.tagName + ':' + (e.placeholder || '')).slice(0,10)")
                print("Inputs:", inputs)
                ctx.close()
                return

            urls = [
                "https://www.mercadolivre.com.br/cupons",
                "https://www.mercadolivre.com.br/p/MLB28083897",
            ]
            ta.fill("\n".join(urls))
            print("URLs coladas")
            page.wait_for_timeout(2000)

            botao = page.query_selector("button:has-text('Gerar')")
            if botao:
                botao.click(force=True)
                print("Gerar clicado")
                page.wait_for_timeout(15000)
                page.screenshot(path=os.path.join(SHOT_DIR, "gerador_cupom_result.png"))

                # Extrair links meli.la
                vals = page.eval_on_selector_all("input, textarea", "els => els.map(e => e.value || e.textContent).filter(v => v && v.includes('meli.la'))")
                texts_all = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0).map(e => e.textContent).filter(t => t && t.includes('meli.la'))")
                todos = vals + texts_all
                links = []
                vistos = set()
                for v in todos:
                    for m in re.findall(r'https?://meli\.la/\w+', v):
                        if m not in vistos:
                            vistos.add(m)
                            links.append(m)
                print(f"Links gerados: {links}")
            else:
                print("Botão Gerar não encontrado")
                texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 25)")
                print("Textos:", [t for t in texts if len(t) < 70][:12])
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
