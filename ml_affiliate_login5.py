#!/usr/bin/env python3
"""Passo 5: escolher verificação por E-MAIL (envia código para o Gmail do Renato)."""
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
            page.goto("https://afiliados.mercadolivre.com.br/", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(7000)
            print(f"URL: {page.url}")

            # Clicar "Já tenho conta" se necessário
            el = page.query_selector("text=Já tenho conta")
            if el:
                el.click()
                page.wait_for_timeout(6000)

            # Procurar e clicar na opção E-mail
            # Tenta várias formas de localizar
            email_opt = None
            for sel in ["text=E-mail", "text=Enviar por e-mail", "[data-testid*='email' i]", "text=re***o2@gmail.com"]:
                email_opt = page.query_selector(sel)
                if email_opt:
                    print(f"✅ Encontrou: {sel}")
                    break

            if email_opt:
                email_opt.click()
                print("✅ Clicou em E-mail")
                page.wait_for_timeout(8000)
            else:
                print("⚠️ Opção E-mail não encontrada diretamente")
                # Tentar por texto parcial
                all_texts = page.eval_on_selector_all("div,span,button,li,a", "els => els.map(e => ({t: e.textContent.trim().slice(0,60), tag: e.tagName}))")
                for item in all_texts:
                    if "email" in item["t"].lower() or "E-mail" in item["t"]:
                        print(f"  candidato: <{item['tag']}> {item['t']}")

            page.screenshot(path=os.path.join(SHOT_DIR, "email_screen.png"))
            print(f"Screenshot: {os.path.join(SHOT_DIR, 'email_screen.png')}")

            # Ver se pede código agora
            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 40)")
            print("Textos:")
            for t in texts[:25]:
                print("  -", t[:90])
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
