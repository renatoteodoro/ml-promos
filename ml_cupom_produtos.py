#!/usr/bin/env python3
"""Investigar cupom: abrir página de cupons, clicar Conferir, ver produtos com cupom."""
import os, sys, json, time, re
from playwright.sync_api import sync_playwright

USER_DATA_DIR = os.path.expanduser("~/.hermes/ml-affiliate/chromium-data")
COOKIES_PATH = os.path.expanduser("~/.hermes/ml-affiliate/cookies_portal.json")

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

            page.goto("https://www.mercadolivre.com.br/cupons", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(10000)
            body = page.inner_text("body")
            print("Cupons:", [l.strip() for l in body.split(chr(10)) if 'OFF' in l or ('R$' in l and 'min' not in l)][:8])

            btn = page.query_selector("button:has-text('Conferir')")
            if btn:
                btn.click(force=True)
                page.wait_for_timeout(8000)
                print("Clicou Conferir")
                print("URL:", page.url[:90])
                body2 = page.inner_text("body")
                links = page.eval_on_selector_all("a", "els => els.map(e => e.href).filter(h => h && h.indexOf('/p/MLB') >= 0)")
                print(f"Produtos /p/MLB: {len(links)}")
                for l in links[:5]:
                    print("  ", l[:70])
                for m in re.finditer(r"com cupom", body2, re.I):
                    s = max(0, m.start()-120)
                    print("CTX:", body2[s:m.end()+60].replace(chr(10), " ")[:180])
                    break
            else:
                print("Botão Conferir não encontrado")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
