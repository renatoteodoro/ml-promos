#!/usr/bin/env python3
"""Clicar nos cards Campanhas exclusivas / Campanhas com incentivos do hub."""
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
            page.goto("https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(12000)

            for nome in ["Campanhas exclusivas", "Campanhas com incentivos"]:
                el = page.query_selector(f"text={nome}")
                if el:
                    print(f"[{nome}] encontrado, clicando...")
                    try:
                        el.click(force=True)
                        page.wait_for_timeout(10000)
                        print(f"    URL: {page.url}")
                        page.screenshot(path=os.path.join(SHOT_DIR, f"hub_{nome.split()[0].lower()}.png"))
                        texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 45)")
                        rel = [t for t in texts if len(t) < 100 and not t.startswith('Rua Trieste') and not t.startswith('Categorias') and not t.startswith('Veículos')]
                        print("    Conteúdo:")
                        for t in rel[:18]:
                            print("      -", t)
                    except Exception as e:
                        print(f"    ERRO: {str(e)[:80]}")
                    # Voltar para o hub
                    page.goto("https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true", timeout=30000, wait_until="domcontentloaded")
                    page.wait_for_timeout(8000)
                else:
                    print(f"[{nome}] NÃO encontrado")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
