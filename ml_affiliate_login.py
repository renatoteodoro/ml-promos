#!/usr/bin/env python3
"""Login no portal de afiliados do ML via Playwright com sessão persistente.
Fluxo: abre o portal, se não estiver logado mostra o QR code (ou página de login)
para o Renato escanear com o app do ML. Sessão fica salva em user-data-dir.
Uso:
  python3 ml_affiliate_login.py           # abre portal e salva QR/página
  python3 ml_affiliate_login.py --qr      # só gera o QR de login (se houver)
  python3 ml_affiliate_login.py --check   # verifica se a sessão está logada
"""
import os, sys, time, json, argparse

USER_DATA_DIR = os.path.expanduser("~/.hermes/ml-affiliate/chromium-data")
SHOT_DIR = os.path.expanduser("~/.hermes/ml-affiliate")
PORTAL_URL = "https://afiliados.mercadolivre.com.br/"
TARGET = "https://www.mercadolivre.com.br/p/MLB28083897"

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
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="Verifica sessão logada")
    ap.add_argument("--shot", default="", help="Nome do screenshot")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = get_browser(p)
        page = ctx.new_page()
        try:
            page.goto(PORTAL_URL, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)  # deixa o JS rodar

            url_atual = page.url
            title = page.title()
            print(f"URL: {url_atual}")
            print(f"Title: {title}")

            # Verificar se está logado (URL do portal vs página de login/verificação)
            logado = "afiliados.mercadolivre.com.br" in url_atual and "login" not in url_atual.lower() and "suspicious" not in url_atual.lower()

            shot_name = args.shot or ("portal_logado.png" if logado else "portal_login.png")
            shot_path = os.path.join(SHOT_DIR, shot_name)
            page.screenshot(path=shot_path, full_page=False)
            print(f"Screenshot: {shot_path}")

            # Procurar QR code na página (img com qr ou canvas)
            qr_srcs = page.eval_on_selector_all(
                "img[src*='qr'], img[src*='QR'], canvas, img[alt*='qr'], img[alt*='QR']",
                "els => els.map(e => e.src || e.tagName)"
            )
            if qr_srcs:
                print(f"QR encontrado: {qr_srcs[:3]}")
                # Salvar o QR em arquivo separado se for imagem
                for i, src in enumerate(qr_srcs):
                    if src.startswith("http"):
                        import urllib.request
                        try:
                            urllib.request.urlretrieve(src, os.path.join(SHOT_DIR, f"qr_{i}.png"))
                            print(f"QR salvo: {os.path.join(SHOT_DIR, f'qr_{i}.png')}")
                        except Exception as e:
                            print(f"QR download falhou: {e}")
            else:
                # Procurar qualquer elemento com texto 'QR'
                has_qr_text = page.query_selector("text=QR Code") or page.query_selector("text=Código QR")
                print(f"Tem texto QR: {bool(has_qr_text)}")

            if logado:
                print("STATUS: LOGADO ✓")
            else:
                print("STATUS: NÃO LOGADO — precisa login (QR ou página de login)")

            # Salvar estado da sessão para diagnóstico
            cookies = ctx.cookies()
            with open(os.path.join(SHOT_DIR, "cookies_info.json"), "w") as f:
                json.dump([{"name": c["name"], "domain": c["domain"]} for c in cookies], f, indent=1)
            print(f"Cookies: {len(cookies)}")

        finally:
            ctx.close()

if __name__ == "__main__":
    main()
