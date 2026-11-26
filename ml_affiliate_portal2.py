#!/usr/bin/env python3
"""Explorar o portal de afiliados logado — descobrir onde fica o Gerador de Links."""
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
            # Ir direto ao portal de afiliados
            page.goto("https://afiliados.mercadolivre.com.br/", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(10000)
            print(f"[1] URL: {page.url}")
            page.screenshot(path=os.path.join(SHOT_DIR, "portal_afiliados.png"))

            # Capturar links da página
            links = page.eval_on_selector_all("a", "els => els.map(e => ({t: e.textContent.trim().slice(0,50), h: e.href})).filter(x => x.t.length > 2).slice(0, 40)")
            print("[2] Links:")
            for l in links:
                print(f"  - {l['t']} → {l['h'][:100]}")

            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 40)")
            print("[3] Textos:")
            for t in texts:
                if len(t) < 95:
                    print("  -", t)
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
