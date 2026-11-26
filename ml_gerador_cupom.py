#!/usr/bin/env python3
"""Testar Gerador de Links com URL de cupom (fluxo do Herói 1)."""
import os, time, sys

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
            # Abrir Gerador de Links
            page.goto("https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(10000)

            # Clicar no Gerador de Links
            link = page.query_selector("a:has-text('Gerador de links')")
            if link:
                href = link.get_attribute("href") or ""
                print(f"Gerador de Links href: {href}")
                page.goto(href, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(12000)
            print(f"URL gerador: {page.url}")
            page.screenshot(path=os.path.join(SHOT_DIR, "gerador_cupom.png"))

            # Colar URL de cupom (produto da BYINTEK que tem "com Cupom")
            textarea = page.query_selector("textarea")
            if textarea:
                url_cupom = "https://www.mercadolivre.com.br/cupons"
                textarea.fill(url_cupom)
                print("URL de cupom colada")
                page.wait_for_timeout(2000)

                # Procurar botão Gerar
                botao = page.query_selector("button:has-text('Gerar')")
                if botao:
                    botao.click(force=True)
                    print("Gerar clicado")
                    page.wait_for_timeout(12000)
                    page.screenshot(path=os.path.join(SHOT_DIR, "gerador_cupom_gerado.png"))

                    # Extrair links gerados
                    texto = page.eval_on_selector_all("input, textarea", "els => els.map(e => e.value).filter(v => v && v.includes('meli.la'))")
                    print("Links gerados:", texto[:3])
                else:
                    print("Botão Gerar não encontrado")
            else:
                print("Textarea não encontrado")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
