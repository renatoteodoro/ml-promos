#!/usr/bin/env python3
"""Procurar o caminho do programa de afiliados no site logado do ML."""
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
            # Procurar link de afiliados na home logada
            page.goto("https://www.mercadolivre.com.br/", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)

            links = page.eval_on_selector_all("a", "els => els.map(e => ({t: e.textContent.trim().slice(0,60), h: e.href})).filter(x => x.t.length > 2)")
            print("[1] Links com 'afiliad' ou 'social':")
            for l in links:
                if 'afiliad' in (l['t'] + l['h']).lower() or 'social' in (l['t'] + l['h']).lower():
                    print(f"  - {l['t']} → {l['h'][:120]}")

            # Tentar URLs conhecidas do programa de afiliados
            print("[2] Testando URLs:")
            for url in [
                "https://www.mercadolivre.com.br/l/afiliados",
                "https://www.mercadolivre.com.br/afiliados",
                "https://afiliados.mercadolivre.com.br/gerador-de-links",
                "https://www.mercadolivre.com.br/social",
                "https://www.mercadolivre.com.br/gz/afiliados",
            ]:
                try:
                    page.goto(url, timeout=25000, wait_until="domcontentloaded")
                    page.wait_for_timeout(4000)
                    final = page.url
                    title = page.title()
                    print(f"  {url}\n    → {final} | {title[:60]}")
                    if "afiliad" in (final + title).lower() and "mercadolivre" in final:
                        page.screenshot(path=os.path.join(SHOT_DIR, "portal_final.png"))
                        texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 30)")
                        for t in texts:
                            if len(t) < 95:
                                print(f"      - {t}")
                        break
                except Exception as e:
                    print(f"  {url}\n    → ERRO: {str(e)[:80]}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
