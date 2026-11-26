#!/usr/bin/env python3
"""Gera links meli.la em BATCH para muitas URLs de uma vez via Gerador de Links.
Testa se o gerador aceita múltiplas URLs (separadas por linha) e retorna todos."""
import os, sys, time, json, re

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
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    from playwright.sync_api import sync_playwright

    # Carregar ofertas do JSON
    with open(os.path.expanduser("~/divulgacao/roteiro_2026-08-08.json")) as f:
        dados = json.load(f)
    ofertas = dados["ofertas"][:n]
    urls = "\n".join(o["link"] for o in ofertas)

    with sync_playwright() as p:
        ctx = get_browser(p)
        page = ctx.new_page()
        try:
            page.goto("https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(10000)

            el = page.query_selector("text=Gerador de links")
            if el:
                el.click(force=True)
                page.wait_for_timeout(8000)
                print("[1] Gerador aberto")

            ta = page.query_selector("textarea:visible")
            if not ta:
                print("[2] ❌ textarea não encontrado")
                return
            ta.fill(urls)
            page.wait_for_timeout(2000)
            print(f"[2] {n} URLs coladas no textarea")

            btn = page.query_selector("button:has-text('Gerar')")
            if btn:
                btn.click(force=True)
                print("[3] Gerar clicado — aguardando...")
                page.wait_for_timeout(25000)
            else:
                print("[3] ❌ botão Gerar não encontrado")
                return

            page.screenshot(path=os.path.join(SHOT_DIR, "batch_gerado.png"))

            # Extrair links meli.la — podem estar em inputs readonly, textareas ou divs
            links = []
            # 1. inputs/textarea com valor meli.la
            vals = page.eval_on_selector_all("input, textarea", "els => els.map(e => e.value || e.textContent).filter(v => v && v.includes('meli.la'))")
            for v in vals:
                links.extend(re.findall(r'https?://meli\.la/\w+', v))
            # 2. elementos com texto meli.la
            texts_all = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0).map(e => e.textContent).filter(t => t && t.includes('meli.la'))")
            for t in texts_all:
                links.extend(re.findall(r'https?://meli\.la/\w+', t))
            # 3. atributos href
            hrefs = page.eval_on_selector_all("a", "els => els.map(e => e.href).filter(h => h && h.includes('meli.la'))")
            links.extend(hrefs)
            # deduplicar preservando ordem
            vistos = set()
            unicos = []
            for l in links:
                if l not in vistos:
                    vistos.add(l)
                    unicos.append(l)
            print(f"[4] Links encontrados: {len(unicos)}")
            for l in unicos[:n]:
                print("  -", l)

            # Textos da página
            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 30)")
            print("[5] Textos:")
            for t in texts[:20]:
                if len(t) < 95:
                    print("  -", t)
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
