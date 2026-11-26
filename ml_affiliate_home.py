#!/usr/bin/env python3
"""Tentar /l/afiliados-home e verificar status do programa de afiliados."""
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
            for url in [
                "https://www.mercadolivre.com.br/l/afiliados-home",
                "https://www.mercadolivre.com.br/afiliados#menu-user",
            ]:
                print(f"=== {url} ===")
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
                page.wait_for_timeout(9000)
                print(f"URL final: {page.url}")
                page.screenshot(path=os.path.join(SHOT_DIR, f"afiliados_{len(url)}.png"))

                texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 30)")
                achou = False
                for t in texts:
                    if any(k in t.lower() for k in ["afiliad", "comissão", "comissao", "link", "ganhe"]):
                        print(f"  ✦ {t[:95]}")
                        achou = True
                if not achou:
                    print("  (sem texto de afiliados — redirecionou)")
                print()
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
