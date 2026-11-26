#!/usr/bin/env python3
"""Passo 9: digitar o código OTP e completar login no portal de afiliados."""
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
    codigo = sys.argv[1] if len(sys.argv) > 1 else "000000"
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = get_browser(p)
        page = ctx.new_page()
        try:
            page.goto("https://afiliados.mercadolivre.com.br/", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            print(f"[1] URL: {page.url}")

            # Se precisar, refazer o caminho: Já tenho conta → e-mail → Continuar
            el = page.query_selector("text=Já tenho conta")
            if el:
                el.click()
                page.wait_for_timeout(6000)
                campo = page.query_selector("input:visible")
                if campo:
                    campo.fill("renatoteodoro2@gmail.com")
                    page.wait_for_timeout(1500)
                    btn = page.query_selector("button:has-text('Continuar')") or page.query_selector("button[type='submit']")
                    if btn:
                        btn.click(force=True)
                        page.wait_for_timeout(9000)

            print(f"[2] URL: {page.url}")

            # Clicar E-mail se estiver na tela de métodos
            opt = page.query_selector("text=re***o2@gmail.com")
            if opt:
                opt.click(force=True)
                page.wait_for_timeout(9000)
                print("[3] Opção E-mail clicada")

            # Encontrar o campo de código — pode ser um input único ou 6 inputs
            print("[4] Procurando campo de código...")
            inputs = page.query_selector_all("input:visible")
            print(f"    inputs visíveis: {len(inputs)}")

            if inputs:
                if len(inputs) == 1:
                    inputs[0].fill(codigo)
                    print(f"[5] Código {codigo} digitado (1 input)")
                else:
                    # 6 inputs individuais (um por dígito)
                    for i, inp in enumerate(inputs[:6]):
                        if i < len(codigo):
                            inp.fill(codigo[i])
                    print(f"[5] Código {codigo} digitado (6 inputs)")

                page.wait_for_timeout(1500)
                page.screenshot(path=os.path.join(SHOT_DIR, "codigo_digitado.png"))

                # Clicar Confirmar
                btn = page.query_selector("button:has-text('Confirmar')") or page.query_selector("button[type='submit']")
                if btn:
                    btn.click(force=True)
                    page.wait_for_timeout(12000)
                    print("[6] Confirmar clicado")
            else:
                print("[4] Nenhum input visível — screenshot abaixo")

            page.screenshot(path=os.path.join(SHOT_DIR, "apos_confirmar.png"))
            print(f"[7] URL final: {page.url}")

            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 35)")
            print("--- Textos ---")
            for t in texts:
                if len(t) < 95:
                    print("  -", t)

            # Salvar cookies da sessão logada
            cookies = ctx.cookies()
            import json
            with open(os.path.join(SHOT_DIR, "cookies_final.json"), "w") as f:
                json.dump([{"name": c["name"], "domain": c["domain"], "path": c["path"], "value": c["value"][:10] + "..."} for c in cookies], f, indent=1)
            print(f"[8] Cookies: {len(cookies)}")
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
