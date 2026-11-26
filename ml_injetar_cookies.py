#!/usr/bin/env python3
"""Injeta cookies do portal ML no perfil Chromium persistente e verifica login.
Uso: python3 ml_injetar_cookies.py [--teste]
"""
import os, sys, json, time

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

    # Converter para o formato do Playwright
    pw_cookies = []
    for c in cookies:
        ss = c.get("sameSite") or "Lax"
        if ss == "no_restriction":
            ss = "None"
        elif ss == "lax":
            ss = "Lax"
        elif ss == "strict":
            ss = "Strict"
        elif ss not in ("Strict", "Lax", "None"):
            ss = "Lax"
        pw = {
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": c.get("path", "/"),
            "secure": c.get("secure", False),
            "httpOnly": c.get("httpOnly", False),
            "sameSite": ss,
        }
        if c.get("expirationDate"):
            pw["expires"] = c["expirationDate"]
        pw_cookies.append(pw)

    with sync_playwright() as p:
        ctx = get_browser(p)
        page = ctx.new_page()
        try:
            # Primeiro navegar para o domínio (para poder setar cookies)
            page.goto("https://www.mercadolivre.com.br", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            # Adicionar cookies
            ctx.add_cookies(pw_cookies)
            print(f"✅ {len(pw_cookies)} cookies injetados")

            # Testar: abrir o hub de afiliados
            page.goto("https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(10000)
            print(f"URL: {page.url}")

            # Verificar se está logado (procura por elementos do hub)
            textos = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 40)")
            logado = any("RENATO" in t.upper() for t in textos) or "hub" in page.url
            tem_login = "iniciar sessão" in " ".join(textos).lower() or "account-verification" in page.url

            page.screenshot(path=os.path.join(SHOT_DIR, "cookies_testado.png"))
            if tem_login and not logado:
                print("❌ AINDA PEDE LOGIN (cookies não funcionaram)")
            elif logado:
                print("✅ PORTAL LOGADO! Cookies funcionando!")
            else:
                print("⚠️ Ambíguo — ver screenshot")
            # Mostrar alguns textos
            print("Textos:", [t for t in textos if len(t) < 60][:10])
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
