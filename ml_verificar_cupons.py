#!/usr/bin/env python3
"""Verificar a ferramenta Cupons no Hub de Afiliados do ML (sessão salva)."""
import os, sys, time

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
            page.goto("https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(12000)
            print(f"[1] URL: {page.url}")

            # Procurar e clicar em "Cupons"
            el = None
            for sel in ["text=Cupons", "text=Cupom"]:
                el = page.query_selector(sel)
                if el:
                    print(f"[2] Encontrou: {sel}")
                    el.click(force=True)
                    break
            if not el:
                print("[2] Cupons não encontrado — listando textos")
                texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 40)")
                for t in texts:
                    if len(t) < 90:
                        print("  -", t)
                ctx.close()
                return

            page.wait_for_timeout(12000)
            print(f"[3] URL após clicar: {page.url}")
            page.screenshot(path=os.path.join(SHOT_DIR, "cupons_tela.png"))

            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 50)")
            print("[4] Textos da tela de cupons:")
            for t in texts:
                if len(t) < 100:
                    print("  -", t)
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
