#!/usr/bin/env python3
"""Passo 8: fluxo completo robusto — login → e-mail → opção E-mail → tela do código."""
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

def textos(page, n=45):
    return page.eval_on_selector_all("body *", f"els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, {n})")

def main():
    email = "renatoteodoro2@gmail.com"
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = get_browser(p)
        page = ctx.new_page()
        try:
            page.goto("https://afiliados.mercadolivre.com.br/", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            print(f"[1] URL: {page.url}")

            # Clicar "Já tenho conta"
            el = page.query_selector("text=Já tenho conta")
            if el:
                el.click()
                page.wait_for_timeout(6000)
                print("[2] Já tenho conta clicado")

            # Digitar e-mail
            campo = page.query_selector("input:visible")
            if campo:
                campo.fill(email)
                page.wait_for_timeout(1500)
                print("[3] E-mail digitado")
                # Continuar
                btn = page.query_selector("button:has-text('Continuar')") or page.query_selector("button[type='submit']")
                if btn:
                    btn.click(force=True)
                    page.wait_for_timeout(9000)
                    print("[4] Continuar clicado")

            print(f"[5] URL: {page.url}")
            page.screenshot(path=os.path.join(SHOT_DIR, "verif2.png"))

            # Listar opções da tela de verificação
            print("--- Opções visíveis ---")
            for t in textos(page, 30):
                print("  -", t[:90])

            # Clicar na opção E-mail (procura o texto com o email mascarado)
            opt = None
            for sel in ["text=re***o2@gmail.com", "text=E-mail", "text=Enviar código para"]:
                opt = page.query_selector(sel)
                if opt:
                    print(f"[6] Encontrou: {sel}")
                    break
            if opt:
                opt.click(force=True)
                page.wait_for_timeout(9000)
                print("[7] Opção E-mail clicada — código enviado para o Gmail!")
                page.screenshot(path=os.path.join(SHOT_DIR, "codigo2.png"))
                print("--- Tela após escolher e-mail ---")
                for t in textos(page, 25):
                    print("  -", t[:90])
            else:
                print("[6] Opção E-mail não encontrada")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
