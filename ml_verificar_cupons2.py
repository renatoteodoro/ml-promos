#!/usr/bin/env python3
"""Verificar seções de Cupons/Campanhas no Hub de Afiliados (o que o outro grupo usa)."""
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
            page.goto("https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(12000)
            print(f"[1] URL: {page.url}")

            # Listar TODOS os links da página (ferramentas do hub)
            links = page.eval_on_selector_all("a", "els => els.map(e => ({t: e.textContent.trim().slice(0,50), h: e.href})).filter(x => x.t.length > 2)")
            print("[2] Links relevantes do hub:")
            for l in links:
                if any(k in (l['t'] + l['h']).lower() for k in ['cupom', 'campanha', 'incentivo', 'link', 'etiqueta', 'lista', 'video', 'colaborador']):
                    print(f"  ✦ {l['t']} → {l['h'][:110]}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
