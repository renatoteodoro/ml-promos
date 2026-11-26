#!/usr/bin/env python3
"""Login ML v2: navega até a tela de código, envia o código UMA vez,
e fica em polling aguardando o arquivo ~/.hermes/ml-affiliate/codigo.txt
conter o código (escrito por mim quando o Renato mandar).
Uso:
  python3 ml_affiliate_espera2.py &
  echo "123456" > ~/.hermes/ml-affiliate/codigo.txt
"""
import os, sys, time

USER_DATA_DIR = os.path.expanduser("~/.hermes/ml-affiliate/chromium-data")
SHOT_DIR = os.path.expanduser("~/.hermes/ml-affiliate")
CODIGO_FILE = os.path.join(SHOT_DIR, "codigo.txt")

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

    # Limpar arquivo de código antigo
    if os.path.exists(CODIGO_FILE):
        os.remove(CODIGO_FILE)

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

            opt = page.query_selector("text=re***o2@gmail.com")
            if not opt:
                opt = page.query_selector("text=E-mail")
            if opt:
                opt.click(force=True)
                page.wait_for_timeout(6000)
                print("[2] CÓDIGO ENVIADO para o e-mail — aguardando codigo.txt...", flush=True)
            else:
                print("[2] Já na tela do código (ou opção não achada)", flush=True)

            # Polling pelo arquivo de código (até 5 min)
            print("[3] Aguardando você me mandar o código...", flush=True)
            codigo = ""
            deadline = time.time() + 300
            while time.time() < deadline:
                if os.path.exists(CODIGO_FILE):
                    with open(CODIGO_FILE) as f:
                        codigo = f.read().strip()
                    if codigo:
                        break
                time.sleep(2)

            if not codigo:
                print("[4] TIMEOUT: nenhum código em 5 min", flush=True)
                return

            print(f"[4] Código: {codigo}", flush=True)
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
                print("[5] Confirmar clicado", flush=True)

            page.screenshot(path=os.path.join(SHOT_DIR, "apos_confirmar3.png"))
            print(f"[6] URL final: {page.url}", flush=True)
            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 30)")
            for t in texts:
                if len(t) < 95:
                    print("  -", t, flush=True)
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
