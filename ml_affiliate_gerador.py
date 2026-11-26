#!/usr/bin/env python3
"""Acessar o Gerador de Links do portal de afiliados e gerar link meli.la."""
import os, sys, time, json, urllib.parse

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
    produto = sys.argv[1] if len(sys.argv) > 1 else "https://www.mercadolivre.com.br/p/MLB28083897"
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = get_browser(p)
        page = ctx.new_page()
        try:
            # URL do gerador de links
            page.goto("https://www.mercadolivre.com.br/l/afiliados-gere-seus-links", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(8000)
            print(f"[1] URL: {page.url}")

            page.screenshot(path=os.path.join(SHOT_DIR, "gerador_tela.png"))

            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 40)")
            print("[2] Textos:")
            for t in texts:
                if len(t) < 95:
                    print("  -", t)

            # Procurar campo de input e botão gerar
            inputs = page.query_selector_all("input:visible")
            print(f"[3] Inputs visíveis: {len(inputs)}")
            for i, inp in enumerate(inputs):
                ph = inp.get_attribute("placeholder") or ""
                print(f"    input[{i}]: type={inp.get_attribute('type')} placeholder={ph}")

            btns = page.query_selector_all("button:visible")
            print(f"[4] Botões visíveis: {len(btns)}")
            for i, b in enumerate(btns):
                print(f"    btn[{i}]: {b.text_content().strip()[:60]}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
