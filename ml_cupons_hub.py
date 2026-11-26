#!/usr/bin/env python3
"""Verificar a ferramenta Cupons/Campanhas no Hub de Afiliados (sessão logada)."""
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
            print(f"URL: {page.url}")

            # Procurar TODOS os elementos clicáveis com texto relacionado a cupom/campanha
            textos = page.eval_on_selector_all("div,span,button,a,li", "els => els.map(e => ({t: (e.textContent||'').trim().slice(0,60), tag: e.tagName})).filter(x => x.t.length > 2 && /cupom|campanha|incentivo|etiqueta/i.test(x.t))")
            print("Elementos cupom/campanha:")
            vistos = set()
            for t in textos[:20]:
                if t['t'] not in vistos:
                    vistos.add(t['t'])
                    print(f"  <{t['tag']}> {t['t']}")

            # Screenshot do hub
            page.screenshot(path=os.path.join(SHOT_DIR, "hub_ferramentas.png"))
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
