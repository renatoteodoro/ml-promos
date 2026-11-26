#!/usr/bin/env python3
"""Passo 3: digitar e-mail no login do ML e avançar para o OTP."""
import os, sys, time, json

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
    email = sys.argv[1] if len(sys.argv) > 1 else "renatoteodoro2@gmail.com"
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = get_browser(p)
        page = ctx.new_page()
        try:
            page.goto("https://www.mercadolivre.com.br/gz/account-verification?go=https%3A%2F%2Fafiliados.mercadolivre.com.br%2F&tid=ef1a0fcb-25de-4dae-86bc-f5b8cd14124f", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

            # Clicar "Já tenho conta"
            el = page.query_selector("text=Já tenho conta")
            if el:
                el.click()
                page.wait_for_timeout(5000)

            # Digitar e-mail
            campo = page.query_selector("input[name='user_id'], input[type='text'], input[type='email'], input#user_id")
            if not campo:
                # procurar por label
                campo = page.query_selector("input")
            if campo:
                campo.fill(email)
                print(f"✅ E-mail digitado: {email}")
                page.wait_for_timeout(1000)
                page.screenshot(path=os.path.join(SHOT_DIR, "login_email.png"))

                # Clicar Continuar
                btn = page.query_selector("button:has-text('Continuar')") or page.query_selector("button[type='submit']")
                if btn:
                    btn.click()
                    print("✅ Continuar clicado")
                    page.wait_for_timeout(8000)
            else:
                print("❌ Campo de e-mail não encontrado")
                page.screenshot(path=os.path.join(SHOT_DIR, "login_erro.png"))

            print(f"URL final: {page.url}")
            page.screenshot(path=os.path.join(SHOT_DIR, "login_pos_email.png"))

            # Textos visíveis
            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 50)")
            print("Textos:")
            for t in texts[:30]:
                print("  -", t[:90])
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
