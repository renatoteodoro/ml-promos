#!/usr/bin/env python3
"""Explorar o Hub de Afiliados — encontrar o Gerador de Links."""
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
            page.goto("https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true#menu-user", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(12000)
            print(f"[1] URL: {page.url}")
            page.screenshot(path=os.path.join(SHOT_DIR, "hub_afiliados.png"))

            links = page.eval_on_selector_all("a", "els => els.map(e => ({t: e.textContent.trim().slice(0,70), h: e.href})).filter(x => x.t.length > 2).slice(0, 60)")
            print("[2] Links:")
            for l in links:
                if any(k in l['t'].lower() for k in ['link', 'gerador', 'gerar', 'afiliad', 'social', 'criador', 'comiss']):
                    print(f"  ✦ {l['t']} → {l['h'][:120]}")

            print("[3] Todos os links (amostra):")
            for l in links[:25]:
                print(f"  - {l['t'][:55]} → {l['h'][:80]}")

            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 35)")
            print("[4] Textos:")
            for t in texts:
                if len(t) < 95:
                    print("  -", t)
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
