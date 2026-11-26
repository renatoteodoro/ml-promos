#!/usr/bin/env python3
"""Capturar tela atual do login ML (estado da verificação)."""
import os, time

USER_DATA_DIR = os.path.expanduser("~/.hermes/ml-affiliate/chromium-data")
SHOT_DIR = os.path.expanduser("~/.hermes/ml-affiliate")

def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            USER_DATA_DIR, headless=True, viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="pt-BR")
        page = ctx.new_page()
        try:
            # Ver em qual página estamos (usar a página ativa do contexto)
            for pg in ctx.pages:
                print(f"Página: {pg.url}")
                if "account-verification" in pg.url or "login" in pg.url:
                    pg.screenshot(path=os.path.join(SHOT_DIR, "login_estado.png"))
                    # Textos
                    texts = pg.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 40)")
                    print("Textos:")
                    for t in texts:
                        if len(t) < 100:
                            print(f"  - {t}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
