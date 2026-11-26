#!/usr/bin/env python3
"""Investigar Campanhas exclusivas + Campanhas com incentivos no hub de afiliados."""
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

            # Tentar rotas prováveis de campanhas
            rotas = [
                "https://www.mercadolivre.com.br/afiliados/campanhas",
                "https://www.mercadolivre.com.br/afiliados/campanhas-exclusivas",
                "https://www.mercadolivre.com.br/afiliados/campanhas/incentivos",
                "https://www.mercadolivre.com.br/afiliados/hub/campanhas",
                "https://www.mercadolivre.com.br/l/afiliados-campanhas",
            ]
            for rota in rotas:
                try:
                    page.goto(rota, timeout=25000, wait_until="domcontentloaded")
                    page.wait_for_timeout(6000)
                    url = page.url
                    texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 40)")
                    rel = [t for t in texts if any(k in t.lower() for k in ['campanha', 'cupom', 'incentivo', 'comiss', 'loja', 'exclusiv'])]
                    print(f"=== {rota} → {url} ===")
                    for t in rel[:10]:
                        print("  ✦", t[:90])
                    if not rel:
                        print("  (sem conteúdo relevante)")
                except Exception as e:
                    print(f"=== {rota} === ERRO {str(e)[:60]}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
