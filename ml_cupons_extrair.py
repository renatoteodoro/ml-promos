#!/usr/bin/env python3
"""Extrair cupons ativos da página pública de cupons do ML (como o Herói 1 faz)."""
import os, time

USER_DATA_DIR = os.path.expanduser("~/.hermes/ml-affiliate/chromium-data")
SHOT_DIR = os.path.expanduser("~/.hermes/ml-affiliate")

def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            USER_DATA_DIR, headless=True, viewport={"width": 1280, "height": 1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="pt-BR")
        page = ctx.new_page()
        try:
            page.goto("https://www.mercadolivre.com.br/cupons", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(15000)
            page.screenshot(path=os.path.join(SHOT_DIR, "cupons_geral.png"), full_page=False)
            print(f"URL: {page.url}")

            # Extrair textos dos cards de cupom
            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 80)")
            print("\nTextos (cupons):")
            for t in texts:
                if len(t) < 100 and not any(x in t for x in ['Rua Trieste', 'Categorias', 'Veículos', 'Supermercado', 'Tecnologia', 'Casa e Móveis', 'Eletrodomésticos', 'Esportes', 'Ferramentas', 'Construção', 'Indústria', 'Para seu', 'Pet Shop', 'Saúde', 'Beleza', 'Moda', 'Bebês', 'Brinquedos', 'Imóveis', 'Internacional', 'Mais vendidos', 'Lojas oficiais', 'Ver mais']):
                    print(f"  - {t}")

            # Procurar links de cupom (href)
            links = page.eval_on_selector_all("a", "els => els.map(e => ({t: (e.textContent||'').trim().slice(0,60), h: e.href})).filter(x => x.t.length > 2 && /cupon|coupon/i.test(x.h))")
            print(f"\nLinks de cupom ({len(links)}):")
            for l in links[:10]:
                print(f"  ✦ {l['t'][:50]} → {l['h'][:110]}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
