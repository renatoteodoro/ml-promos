#!/usr/bin/env python3
"""Capturar telas completas de exclusive-campaigns e incentives (espera o JS renderizar)."""
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
            for nome, rota in [("campanhas_exclusivas", "exclusive-campaigns"), ("incentivos", "incentives")]:
                page.goto(f"https://www.mercadolivre.com.br/afiliados/{rota}#menu-lateral", timeout=45000, wait_until="domcontentloaded")
                # Esperar renderização do conteúdo dinâmico
                page.wait_for_timeout(15000)
                # Scroll para carregar tudo
                for y in range(0, 3000, 600):
                    page.mouse.wheel(0, 600)
                    page.wait_for_timeout(800)
                page.mouse.wheel(0, -3000)
                page.wait_for_timeout(1500)
                shot = os.path.join(SHOT_DIR, f"hub_{nome}.png")
                page.screenshot(path=shot, full_page=True)
                print(f"✅ {nome}: {shot}")

                # Extrair textos (depois do JS)
                texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 60)")
                print(f"  Textos de {nome}:")
                for t in texts:
                    if len(t) < 110 and not any(x in t for x in ['Rua Trieste', 'Categorias', 'Veículos', 'Supermercado', 'Tecnologia', 'Casa e Móveis', 'Eletrodomésticos', 'Esportes', 'Ferramentas', 'Construção', 'Indústria', 'Para seu', 'Pet Shop', 'Saúde', 'Beleza', 'Moda', 'Bebês', 'Brinquedos', 'Imóveis', 'Internacional', 'Mais vendidos', 'Lojas oficiais', 'Ver mais']):
                        print(f"    - {t}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
