#!/usr/bin/env python3
"""Entrar na ferramenta 'Cupons' do hub de afiliados."""
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

            # Encontrar o botão "Cupons" (a ferramenta, não o link do site)
            # O hub tem cards de ferramentas — procurar o card Cupons
            el = page.query_selector("text=Cupons")
            if el:
                print("Encontrado elemento Cupons, clicando...")
                el.click(force=True)
                page.wait_for_timeout(12000)
                print(f"URL após clique: {page.url}")
                page.screenshot(path=os.path.join(SHOT_DIR, "ferramenta_cupons.png"))

                texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 50)")
                print("Textos:")
                for t in texts:
                    if len(t) < 100 and not t.startswith('function') and 'window' not in t:
                        print("  -", t)
            else:
                print("Cupons não encontrado")
                # Listar todos os botões
                btns = page.eval_on_selector_all("button, a", "els => els.map(e => ({t: (e.textContent||'').trim().slice(0,40), tag: e.tagName})).filter(x => x.t.length > 2)")
                for b in btns[:30]:
                    print(f"  <{b['tag']}> {b['t']}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
