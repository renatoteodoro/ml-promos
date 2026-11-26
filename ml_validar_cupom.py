#!/usr/bin/env python3
"""Validar detecção com produto que SABEMOS ter cupom (Wanbo R$35 OFF)."""
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

            # Pegar o link /p/MLB do produto Wanbo na página da campanha
            page.goto("https://lista.mercadolivre.com.br/pagina/fl20250612203232/?coupon_campaign_id=13328543", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(8000)
            links = page.eval_on_selector_all("a", "els => els.map(e => e.href).filter(h => h && h.indexOf('/p/MLB') >= 0)")
            print(f"Produtos da campanha: {len(links)}")
            if not links:
                ctx.close()
                return
            url = links[0]
            print("Testando:", url[:70])

            # Detectar cupom no produto principal
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(8000)
            body = page.inner_text("body").lower()
            idx = body.find("produtos relacionados")
            if idx > 0:
                body = body[:idx]
            if "com cupom" in body:
                m = re.search(r"(\d+%)\s*off\s*com cupom", body)
                mc = re.search(r"cupom\s*[:\s]*([A-Z0-9]{4,12})", body)
                print(f"✅ CUPOM DETECTADO! {m.group(1) if m else '?'} código: {mc.group(1) if mc else '(sem código visível)'}")
                # Mostrar contexto
                for mm in re.finditer(r"com cupom", body):
                    s = max(0, mm.start()-80)
                    print("  CTX:", body[s:mm.end()+40].replace(chr(10), " ")[:150])
            else:
                print("❌ Sem cupom no produto principal")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
