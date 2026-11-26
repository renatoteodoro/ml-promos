#!/usr/bin/env python3
"""Extrair CÓDIGO de cupom da página pública (clicar Conferir) + testar gerar meli.la de cupom."""
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

            # Clicar no primeiro botão "Conferir" ou "Aplicar"
            botao = page.query_selector("button:has-text('Conferir'), button:has-text('Aplicar')")
            if botao:
                print("Botão encontrado, clicando...")
                botao.click(force=True)
                page.wait_for_timeout(8000)
                page.screenshot(path=os.path.join(SHOT_DIR, "cupom_aberto.png"))

                # Extrair todos os textos da tela (código pode aparecer)
                texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 60)")
                print("\nTextos após clicar:")
                for t in texts:
                    if len(t) < 110 and not any(x in t for x in ['Rua Trieste', 'Categorias', 'Veículos', 'Supermercado', 'Tecnologia', 'Casa e Móveis', 'Eletrodomésticos', 'Esportes', 'Ferramentas', 'Construção', 'Indústria', 'Para seu', 'Pet Shop', 'Saúde', 'Beleza', 'Moda', 'Bebês', 'Brinquedos', 'Imóveis', 'Internacional', 'Mais vendidos', 'Lojas oficiais', 'Ver mais', 'Produtos Sustent']):
                        print(f"  - {t}")
            else:
                print("Nenhum botão Conferir/Aplicar visível")
                texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 30)")
                for t in texts:
                    if len(t) < 90:
                        print(f"  - {t}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
