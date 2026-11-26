#!/usr/bin/env python3
"""Passo 4b: ir direto para a tela de verificação (sessão já tem o e-mail) e clicar QR."""
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
            # Ir direto ao portal — deve pedir verificação
            page.goto("https://afiliados.mercadolivre.com.br/", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(7000)
            print(f"URL: {page.url}")

            # Procurar "Código QR" direto
            qr_btn = page.query_selector("text=Código QR")
            if qr_btn:
                qr_btn.click()
                print("✅ Clicou em Código QR")
                page.wait_for_timeout(8000)
            else:
                # tentar outros textos
                for t in ["CódigoQR", "QR", "Escanear"]:
                    el = page.query_selector(f"text={t}")
                    if el:
                        el.click()
                        print(f"✅ Clicou em {t}")
                        page.wait_for_timeout(8000)
                        break

            page.screenshot(path=os.path.join(SHOT_DIR, "qr_screen2.png"))
            print(f"Screenshot: {os.path.join(SHOT_DIR, 'qr_screen2.png')}")

            # Procurar imagem QR (img ou canvas)
            qr_img = page.query_selector("img[src*='qr'], img[src*='QR'], canvas, [class*='qr' i], [data-testid*='qr' i]")
            if qr_img:
                try:
                    qr_img.screenshot(path=os.path.join(SHOT_DIR, "qr_code.png"))
                    print(f"QR extraído: {os.path.join(SHOT_DIR, 'qr_code.png')}")
                except Exception as e:
                    print(f"QR extração falhou: {e}")
                    src = qr_img.get_attribute("src")
                    print(f"QR src: {str(src)[:120]}")
                    if src and src.startswith("http"):
                        import urllib.request
                        urllib.request.urlretrieve(src, os.path.join(SHOT_DIR, "qr_code.png"))
                        print("QR baixado do src")
            else:
                print("QR img não encontrada")

            # Textos
            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 40)")
            print("Textos:")
            for t in texts[:25]:
                print("  -", t[:90])
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
