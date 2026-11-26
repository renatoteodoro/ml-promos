#!/usr/bin/env python3
"""Login ML v3: vai direto para a tela de verificação SEM reenviar código,
e digita o código passado por argumento.
Uso: python3 ml_affiliate_otp2.py 663059
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
    codigo = sys.argv[1] if len(sys.argv) > 1 else ""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        ctx = get_browser(p)
        page = ctx.new_page()
        try:
            page.goto("https://afiliados.mercadolivre.com.br/", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)
            print(f"[1] URL: {page.url}", flush=True)

            # Navegar pelo fluxo: Já tenho conta → e-mail → Continuar
            # (NÃO clicar em E-mail novamente — isso reenviaria código!)
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

            print(f"[2] URL: {page.url}", flush=True)

            # Se estiver na tela de métodos, clicar E-mail (REENVIA — necessário se a sessão reiniciou)
            # Verificar primeiro se já está na tela de código
            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 35)")
            na_tela_codigo = any("código que te enviamos" in t.lower() or "codigo que te enviamos" in t.lower() for t in texts)

            if not na_tela_codigo:
                opt = page.query_selector("text=re***o2@gmail.com") or page.query_selector("text=E-mail")
                if opt:
                    opt.click(force=True)
                    page.wait_for_timeout(9000)
                    print("[3] Clicou em E-mail (reenviou código)", flush=True)
                    na_tela_codigo = True
            else:
                print("[3] Já está na tela do código (sem reenviar)", flush=True)

            page.screenshot(path=os.path.join(SHOT_DIR, "otp2_tela.png"))

            # Digitar o código
            inputs = page.query_selector_all("input:visible")
            if len(inputs) >= 6 and len(codigo) == 6:
                for i, inp in enumerate(inputs[:6]):
                    inp.fill(codigo[i])
                print(f"[4] Código {codigo} digitado", flush=True)
                page.wait_for_timeout(1500)
                btn = page.query_selector("button:has-text('Confirmar')") or page.query_selector("button[type='submit']")
                if btn:
                    btn.click(force=True)
                    page.wait_for_timeout(12000)
                    print("[5] Confirmar clicado", flush=True)
            else:
                print(f"[4] inputs={len(inputs)} codigo_len={len(codigo)}", flush=True)

            page.screenshot(path=os.path.join(SHOT_DIR, "otp2_final.png"))
            print(f"[6] URL final: {page.url}", flush=True)
            texts = page.eval_on_selector_all("body *", "els => els.filter(e => e.children.length === 0 && e.textContent.trim().length > 1).map(e => e.textContent.trim()).slice(0, 25)")
            for t in texts:
                if len(t) < 95:
                    print("  -", t, flush=True)
        finally:
            ctx.close()

if __name__ == "__main__":
    main()
