#!/usr/bin/env python3
"""Clicar nos cards de ferramentas do hub (Campanhas exclusivas) via links."""
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

            # Listar TODOS os links do hub com href
            links = page.eval_on_selector_all("a", "els => els.map(e => ({t: (e.textContent||'').trim().slice(0,45), h: e.href})).filter(x => x.t.length > 2 && /campanha|cupom|incentivo|afiliad/i.test(x.h + x.t))")
            print("Links de campanha/cupom encontrados:")
            for l in links[:25]:
                print(f"  ✦ {l['t']} → {l['h'][:100]}")

            # Tentar clicar em cada link de campanha e capturar
            for alvo in ["Campanhas exclusivas", "Campanhas com incentivos"]:
                try:
                    # Procurar link que contém o texto
                    link = page.query_selector(f"a:has-text('{alvo}')")
                    if link:
                        href = link.get_attribute("href") or ""
                        print(f"\n[{alvo}] href: {href}")
                        if href.startswith("http"):
                            page.goto(href, timeout=30000, wait_until="domcontentloaded")
                        else:
                            link.click(force=True)
                        page.wait_for_timeout(10000)
                        print(f"  URL final: {page.url}")
                        page.screenshot(path=os.path.join(SHOT_DIR, f"hub_{alvo.split()[0].lower()}.png"))
                        texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 40)")
                        print("  Conteúdo:")
                        for t in texts:
                            if len(t) < 100 and not any(x in t for x in ['Rua Trieste', 'Categorias', 'Veículos', 'Supermercado']):
                                print(f"    - {t}")
                    else:
                        print(f"[{alvo}] link não encontrado")
                except Exception as e:
                    print(f"[{alvo}] ERRO: {str(e)[:80]}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
