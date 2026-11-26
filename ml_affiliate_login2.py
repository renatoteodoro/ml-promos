#!/usr/bin/env python3
"""Passo 2b: navegar pela tela de login — clicar 'Já tenho conta' e buscar QR."""
import os, sys, time, json

USER_DATA_DIR = os.path.expanduser("~/.hermes/ml-affiliate/chromium-data")
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

    with sync_playwright() as p:
        ctx = get_browser(p)
        page = ctx.new_page()
        try:
            page.goto("https://www.mercadolivre.com.br/gz/account-verification?go=https%3A%2F%2Fafiliados.mercadolivre.com.br%2F&tid=ef1a0fcb-25de-4dae-86bc-f5b8cd14124f", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

            # Clicar em "Já tenho conta"
            for sel in ["text=Já tenho conta", "text=Ya tengo cuenta", "a[href*='login']", "text=Continuar"]:
                el = page.query_selector(sel)
                if el:
                    print(f"Clicando: {sel}")
                    el.click()
                    break

            page.wait_for_timeout(7000)
            print(f"URL: {page.url}")
            page.screenshot(path=os.path.join(SHOT_DIR, "login_tela2.png"))

            # Extrair textos e procurar QR
            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 60)")
            print("Textos:")
            for t in texts[:35]:
                print("  -", t[:90])

            qr = page.query_selector("img[src*='qr'], img[src*='QR'], canvas, [class*='qr']")
            print(f"QR element: {bool(qr)}")
            if qr:
                qr.screenshot(path=os.path.join(SHOT_DIR, "qr_tela.png"))
                print("QR salvo em qr_tela.png")

        finally:
            ctx.close()

if __name__ == "__main__":
    main()
