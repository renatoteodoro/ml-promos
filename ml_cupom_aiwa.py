#!/usr/bin/env python3
"""Investigar cupom da Smart TV AIWA: código + link do produto + gerar meli.la."""
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

            # Abrir a página da TV AIWA (com cupom)
            with open('/home/hermes/divulgacao/roteiro_2026-08-08.json') as f:
                dados = json.load(f)
            oferta = dados['ofertas'][3]  # Smart TV AIWA
            print("Produto:", oferta['titulo'][:50])
            print("Link:", oferta['link'][:80])

            page.goto(oferta['link'], timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(8000)
            body = page.inner_text("body")
            # Procurar TODOS os trechos com cupom
            print("\n=== Trechos com 'cupom' ===")
            for m in re.finditer(r"[Cc]upom", body):
                s = max(0, m.start()-100)
                print("CTX:", body[s:m.end()+100].replace(chr(10), " ")[:180])
            # Procurar botões de cupom
            botoes = page.eval_on_selector_all("button, span, div", "els => els.filter(e => (e.textContent||'').toLowerCase().indexOf('cupom') >= 0).map(e => e.textContent.trim().slice(0,80)).filter(t => t.length > 2).slice(0, 10)")
            print("\n=== Elementos com cupom ===")
            for b in botoes:
                print("  -", b)
            page.screenshot(path=os.path.join(SHOT_DIR, "tv_aiwa_cupom.png"))
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
