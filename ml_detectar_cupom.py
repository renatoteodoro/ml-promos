#!/usr/bin/env python3
"""Detectar cupom no produto via Playwright (página renderizada com cookies)."""
import os, sys, json, time, re

USER_DATA_DIR = os.path.expanduser("~/.hermes/ml-affiliate/chromium-data")
COOKIES_PATH = os.path.expanduser("~/.hermes/ml-affiliate/cookies_portal.json")

def get_browser(p):
    return p.chromium.launch_persistent_context(
        USER_DATA_DIR, headless=True, viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="pt-BR", args=["--disable-blink-features=AutomationControlled"])

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

            # Testar página do produto PS5
            page.goto("https://www.mercadolivre.com.br/p/MLB28083897", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(8000)
            body = page.inner_text("body")
            print(f"URL: {page.url[:70]}")
            print(f"Tem 'cupom': {'cupom' in body.lower()}")
            print(f"Tem 'com cupom': {'com cupom' in body.lower()}")
            # Procurar trecho com cupom
            for m in re.finditer(r"[Cc]upom", body):
                s = max(0, m.start()-60)
                print("  ...", body[s:m.end()+80].replace(chr(10), " ")[:140])
                if m.start() > 3000:
                    break
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
