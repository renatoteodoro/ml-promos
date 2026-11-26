#!/usr/bin/env python3
"""Login ML: navega até a tela de código UMA vez, espera o código no stdin e confirma.
Uso: echo "236756" | python3 ml_affiliate_espera.py
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
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = get_browser(p)
        page = ctx.new_page()
        try:
            page.goto("https://afiliados.mercadolivre.com.br/", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            print(f"[1] URL: {page.url}", flush=True)

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

            # Clicar E-mail (envia código UMA vez)
            opt = page.query_selector("text=re***o2@gmail.com")
            if not opt:
                opt = page.query_selector("text=E-mail")
            if opt:
                opt.click(force=True)
                page.wait_for_timeout(6000)
                print("[2] CÓDIGO ENVIADO para o e-mail — aguardando você digitar...", flush=True)
            else:
                # Pode já estar na tela do código
                print("[2] Já está na tela do código (ou opção não achada)", flush=True)

            page.screenshot(path=os.path.join(SHOT_DIR, "espera_codigo.png"))

            # Verificar se está na tela de código
            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 30)")
            tem_codigo = any("código" in t.lower() or "codigo" in t.lower() for t in texts)
            print(f"[3] Tela de código: {tem_codigo}", flush=True)
            if not tem_codigo:
                print("[3] Textos:", flush=True)
                for t in texts[:20]:
                    print("   -", t[:90], flush=True)

            # ESPERAR o código via stdin (sem timeout de execução — o processo fica vivo)
            print("[4] PRONTO — me envie o código de 6 dígitos", flush=True)
            codigo = sys.stdin.readline().strip()
            print(f"[5] Código recebido: {codigo}", flush=True)

            if codigo:
                inputs = page.query_selector_all("input:visible")
                if len(inputs) == 6:
                    for i, inp in enumerate(inputs[:6]):
                        if i < len(codigo):
                            inp.fill(codigo[i])
                elif inputs:
                    inputs[0].fill(codigo)
                page.wait_for_timeout(1500)
                btn = page.query_selector("button:has-text('Confirmar')") or page.query_selector("button[type='submit']")
                if btn:
                    btn.click(force=True)
                    page.wait_for_timeout(12000)
                    print("[6] Confirmar clicado", flush=True)

                page.screenshot(path=os.path.join(SHOT_DIR, "apos_confirmar2.png"))
                print(f"[7] URL final: {page.url}", flush=True)
                texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 30)")
                for t in texts:
                    if len(t) < 95:
                        print("  -", t, flush=True)
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
