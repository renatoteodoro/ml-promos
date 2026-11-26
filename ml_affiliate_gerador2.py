#!/usr/bin/env python3
"""Abrir o Gerador de Links no Hub de Afiliados e gerar link para um produto."""
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

            # Procurar e clicar no "Gerador de links"
            el = None
            for sel in ["text=Gerador de links", "text=Gerador de Links", "text=Gerador"]:
                el = page.query_selector(sel)
                if el:
                    print(f"[1] Clicando: {sel}")
                    el.click(force=True)
                    break
            if not el:
                print("[1] Gerador não encontrado como texto — listando botões/links")
                els = page.query_selector_all("a, button")
                for e in els[:30]:
                    t = (e.text_content() or "").strip()
                    if t:
                        print(f"  - {t[:60]}")
                return

            page.wait_for_timeout(10000)
            print(f"[2] URL: {page.url}")
            page.screenshot(path=os.path.join(SHOT_DIR, "gerador_aberto.png"))

            # Extrair conteúdo
            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 40)")
            print("[3] Textos:")
            for t in texts:
                if len(t) < 95:
                    print("  -", t)

            # Inputs e botões
            inputs = page.query_selector_all("input:visible")
            print(f"[4] Inputs: {len(inputs)}")
            for i, inp in enumerate(inputs[:6]):
                print(f"    [{i}] type={inp.get_attribute('type')} ph={inp.get_attribute('placeholder')}")
            btns = page.query_selector_all("button:visible")
            print(f"[5] Botões: {len(btns)}")
            for i, b in enumerate(btns[:10]):
                print(f"    [{i}] {b.text_content().strip()[:50]}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
