#!/usr/bin/env python3
"""Login ML: navega até a tela de verificação e CAPTURA o estado exato (sem enviar código)."""
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
            page.goto("https://afiliados.mercadolivre.com.br/", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            print(f"[1] URL: {page.url}")

            el = page.query_selector("text=Já tenho conta")
            if el:
                el.click()
                page.wait_for_timeout(6000)
                print("[1b] Clicou em 'Já tenho conta'")

            campo = page.query_selector("input:visible")
            if campo:
                campo.fill("renatoteodoro2@gmail.com")
                page.wait_for_timeout(1500)
                btn = page.query_selector("button:has-text('Continuar')") or page.query_selector("button[type='submit']")
                if btn:
                    btn.click(force=True)
                    page.wait_for_timeout(9000)
                    print("[2] Clicou Continuar")

            print(f"[3] URL: {page.url}")
            page.screenshot(path=os.path.join(SHOT_DIR, "login_estado.png"))
            time.sleep(3)

            # Listar TODOS os textos da tela (para entender o que aparece)
            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 50)")
            print("[4] Textos da tela:")
            for t in texts:
                if len(t) < 110:
                    print(f"  - {t}")

            # Listar inputs e botões visíveis
            inputs = page.eval_on_selector_all("input:visible", "els => els.map(e => ({ph: e.placeholder, type: e.type}))")
            print("[5] Inputs visíveis:", inputs)
            botoes = page.eval_on_selector_all("button:visible", "els => els.map(e => e.textContent.trim().slice(0,50)).filter(t => t.length > 1)")
            print("[6] Botões visíveis:", botoes[:10])
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
