#!/usr/bin/env python3
"""Gerar link meli.la no Gerador de Links do Hub de Afiliados.
Uso: python3 ml_affiliate_gerar.py "URL_DO_PRODUTO"
"""
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
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.mercadolivre.com.br/p/MLB28083897"
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = get_browser(p)
        page = ctx.new_page()
        try:
            page.goto("https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true#menu-user", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(12000)

            # Clicar no Gerador de links
            el = page.query_selector("text=Gerador de links") or page.query_selector("text=Gerador de Links")
            if el:
                el.click(force=True)
                page.wait_for_timeout(10000)
                print("[1] Gerador aberto")

            page.screenshot(path=os.path.join(SHOT_DIR, "gerador_form.png"))

            # Encontrar o textarea (campo de URLs) — pode ser textarea ou input
            ta = page.query_selector("textarea:visible")
            if not ta:
                # procurar input com placeholder 'Ex:'
                ta = page.query_selector("input[placeholder*='Ex:'], input[placeholder*='http']")
            if not ta:
                ta = page.query_selector("textarea, input[type='text']:visible")
            if ta:
                ta.fill(url)
                print(f"[2] URL digitada: {url}")
                page.wait_for_timeout(1500)

            # Clicar Gerar
            btn = page.query_selector("button:has-text('Gerar')")
            if btn:
                btn.click(force=True)
                print("[3] Gerar clicado")
                page.wait_for_timeout(12000)
            else:
                print("[3] Botão Gerar não encontrado")

            page.screenshot(path=os.path.join(SHOT_DIR, "link_gerado.png"))
            print(f"[4] URL: {page.url}")

            # Procurar o link gerado (meli.la ou link de afiliado)
            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 45)")
            print("[5] Textos:")
            for t in texts:
                if len(t) < 100:
                    print("  -", t)

            # Procurar links meli.la na página
            links = page.eval_on_selector_all("a", "els => els.map(e => e.href).filter(h => h && (h.includes('meli.la') || h.includes('mercadolivre.com/sec')))")
            print(f"[6] Links meli.la/sec: {links}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
