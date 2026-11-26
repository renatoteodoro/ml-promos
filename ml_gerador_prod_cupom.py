#!/usr/bin/env python3
"""Testar Gerador com o PRODUTO do cupom (link /p/MLB da loja com cupom)."""
import os, sys, json, time, re
from playwright.sync_api import sync_playwright

USER_DATA_DIR = os.path.expanduser("~/.hermes/ml-affiliate/chromium-data")
COOKIES_PATH = os.path.expanduser("~/.hermes/ml-affiliate/cookies_portal.json")
SHOT_DIR = os.path.expanduser("~/.hermes/ml-affiliate")

def main():
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
        ctx = p.chromium.launch_persistent_context(USER_DATA_DIR, headless=True, viewport={"width":1280,"height":900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="pt-BR", args=["--disable-blink-features=AutomationControlled"])
        page = ctx.new_page()
        try:
            page.goto("https://www.mercadolivre.com.br", timeout=30000, wait_until="domcontentloaded")
            ctx.add_cookies(pw_cookies)

            # Pegar o link /p/MLB do produto Wanbo (que tem cupom R$35 OFF)
            page.goto("https://lista.mercadolivre.com.br/pagina/fl20250612203232/?coupon_campaign_id=13328543", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(8000)
            links = page.eval_on_selector_all("a", "els => els.map(e => e.href).filter(h => h && h.indexOf('/p/MLB') >= 0)")
            print(f"Produtos com cupom: {len(links)}")
            if links:
                url_prod = links[0]
                print("Produto:", url_prod[:80])

                # Gerar link do produto
                page.goto("https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true", timeout=45000, wait_until="domcontentloaded")
                page.wait_for_timeout(8000)
                el = page.query_selector("text=Gerador de links")
                if el:
                    el.click(force=True)
                    page.wait_for_timeout(10000)
                ta = page.query_selector("textarea:visible")
                if ta:
                    ta.fill(url_prod)
                    page.wait_for_timeout(2000)
                    botao = page.query_selector("button:has-text('Gerar')")
                    if botao:
                        botao.click(force=True)
                        page.wait_for_timeout(15000)
                        page.screenshot(path=os.path.join(SHOT_DIR, "gerador_prod_cupom.png"))
                        vals = page.eval_on_selector_all("input, textarea", "els => els.map(e => e.value || e.textContent).filter(v => v && v.indexOf('meli.la') >= 0)")
                        texts_all = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0).map(e => e.textContent).filter(t => t && t.indexOf('meli.la') >= 0)")
                        todos = vals + texts_all
                        links_gerados, vistos = [], set()
                        for v in todos:
                            for m in re.findall(r'https?://meli\.la/\w+', v):
                                if m not in vistos:
                                    vistos.add(m)
                                    links_gerados.append(m)
                        print(f"Link gerado: {links_gerados}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
