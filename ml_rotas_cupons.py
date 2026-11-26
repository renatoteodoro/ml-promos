#!/usr/bin/env python3
"""Testar rotas de cupons/campanhas no hub de afiliados."""
import os, sys, time

USER_DATA_DIR = os.path.expanduser("~/.hermes/ml-affiliate/chromium-data")

def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            USER_DATA_DIR, headless=True, viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="pt-BR")
        page = ctx.new_page()
        try:
            for rota in ["https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true#/cupons",
                          "https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true#/campanhas",
                          "https://www.mercadolivre.com.br/afiliados/cupons",
                          "https://www.mercadolivre.com.br/afiliados/campanhas"]:
                try:
                    page.goto(rota, timeout=25000, wait_until="domcontentloaded")
                    page.wait_for_timeout(6000)
                    texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 30)")
                    relevantes = [t for t in texts if any(k in t.lower() for k in ['cupom', 'campanha', 'incentivo', 'código', 'codigo', 'comiss', 'gerar'])]
                    print(f"=== {rota.split('?')[0]}{rota.split('?')[1][:20] if '?' in rota else ''} ===")
                    if relevantes:
                        for t in relevantes[:8]:
                            print("  ✦", t[:90])
                    else:
                        print("  (sem texto relevante)")
                except Exception as e:
                    print(f"=== {rota} === ERRO {str(e)[:70]}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
