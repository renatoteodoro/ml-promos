#!/usr/bin/env python3
"""Testar Gerador de Links com URL de CUPOM (coupon_campaign_id) — o formato do Herói 1!"""
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

            # Abrir o Gerador de Links
            page.goto("https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(8000)
            el = page.query_selector("text=Gerador de links")
            if el:
                el.click(force=True)
                page.wait_for_timeout(10000)
            print("URL gerador:", page.url[:70])

            # Colar URL de CUPOM (a que o Conferir levou) + produto com cupom
            ta = page.query_selector("textarea:visible")
            if not ta:
                print("❌ textarea não encontrado")
                ctx.close()
                return
            urls = [
                "https://lista.mercadolivre.com.br/pagina/fl20250612203232/?coupon_campaign_id=13328543",
                "https://www.mercadolivre.com.br/projetor-inteligente-wanbo-x5-pro-1100-ansilumens-android-11-wifi-dual-p-IML2044894",
            ]
            ta.fill("\n".join(urls))
            print("URLs coladas (cupom + produto)")
            page.wait_for_timeout(2000)
            botao = page.query_selector("button:has-text('Gerar')")
            if botao:
                botao.click(force=True)
                print("Gerar clicado")
                page.wait_for_timeout(15000)
                page.screenshot(path=os.path.join(SHOT_DIR, "gerador_cupom_campaign.png"))
                # Extrair links
                vals = page.eval_on_selector_all("input, textarea", "els => els.map(e => e.value || e.textContent).filter(v => v && v.indexOf('meli.la') >= 0)")
                texts_all = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0).map(e => e.textContent).filter(t => t && t.indexOf('meli.la') >= 0)")
                todos = vals + texts_all
                links, vistos = [], set()
                for v in todos:
                    for m in re.findall(r'https?://meli\.la/\w+', v):
                        if m not in vistos:
                            vistos.add(m)
                            links.append(m)
                print(f"Links gerados: {links}")
                # Ver mensagens de erro
                body = page.inner_text("body")
                for m in re.finditer(r"[Nn]ão é permitido|erro|permitid", body):
                    s = max(0, m.start()-60)
                    print("MSG:", body[s:m.end()+60].replace(chr(10), " ")[:120])
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
