#!/usr/bin/env python3
"""
Detecção de cupons por produto para os posts do Promo das Galáxias.

Fluxo (validado 08/08/2026):
1. Para cada produto da lista do dia, verifica se a página tem "com Cupom"
2. Se tiver, extrai o código do cupom e o desconto
3. Adiciona ao JSON: oferta["cupom"] = {"codigo": "X", "desconto": "20% OFF"}

Uso: python3 ml_detectar_cupons.py [--json roteiro.json]
"""
import os, sys, json, time, re

USER_DATA_DIR = os.path.expanduser("~/.hermes/ml-affiliate/chromium-data")
COOKIES_PATH = os.path.expanduser("~/.hermes/ml-affiliate/cookies_portal.json")

def get_browser(p):
    return p.chromium.launch_persistent_context(
        USER_DATA_DIR, headless=True, viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="pt-BR", args=["--disable-blink-features=AutomationControlled"])

def carregar_cookies():
    with open(COOKIES_PATH) as f:
        cookies = json.load(f)
    pw = []
    for c in cookies:
        ss = c.get("sameSite") or "Lax"
        ss = {"no_restriction": "None", "lax": "Lax", "strict": "Strict"}.get(ss, "Lax")
        item = {"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c.get("path", "/"),
                "secure": c.get("secure", False), "httpOnly": c.get("httpOnly", False), "sameSite": ss}
        if c.get("expirationDate"):
            item["expires"] = c["expirationDate"]
        pw.append(item)
    return pw

def detectar_cupom_produto(page, link_produto):
    """Verifica se o PRODUTO PRINCIPAL tem cupom ativo (ignora produtos relacionados)."""
    try:
        page.goto(link_produto, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        body = page.inner_text("body").lower()
        # Focar apenas na área do produto principal (cortar em "produtos relacionados")
        idx = body.find("produtos relacionados")
        if idx > 0:
            body = body[:idx]
        if "com cupom" in body:
            m = re.search(r"(\d+%)\s*off\s*com cupom", body)
            desc = m.group(1) if m else ""
            mc = re.search(r"cupom\s*[:\s]*([A-Z0-9]{4,12})", body)
            codigo = mc.group(1) if mc else ""
            return {"tem_cupom": True, "desconto_cupom": desc, "codigo_cupom": codigo}
    except Exception as e:
        print(f"    ⚠️ erro: {str(e)[:60]}")
    return None

def processar(ofertas, so_detectados=False):
    """Verifica cupom em cada oferta. Retorna ofertas com campo 'cupom'."""
    from playwright.sync_api import sync_playwright

    cookies = carregar_cookies()
    com_cupom = 0
    with sync_playwright() as p:
        ctx = get_browser(p)
        page = ctx.new_page()
        try:
            page.goto("https://www.mercadolivre.com.br", timeout=30000, wait_until="domcontentloaded")
            ctx.add_cookies(cookies)
            for i, o in enumerate(ofertas):
                link = o.get("link", "")
                if not link:
                    continue
                # Pular se já tem cupom detectado
                if o.get("cupom", {}).get("tem_cupom"):
                    com_cupom += 1
                    continue
                r = detectar_cupom_produto(page, link)
                if r:
                    o["cupom"] = r
                    com_cupom += 1
                    print(f"  🎟️ [{i+1}] {o['titulo'][:40]} → cupom {r['desconto_cupom']} {r['codigo_cupom']}")
                else:
                    o["cupom"] = {"tem_cupom": False}
                if (i + 1) % 10 == 0:
                    print(f"    ...{i+1}/{len(ofertas)} verificados ({com_cupom} com cupom)")
                time.sleep(0.5)
        finally:
            ctx.close()
    print(f"✅ {com_cupom}/{len(ofertas)} ofertas com cupom detectado")
    return ofertas

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.expanduser("~/divulgacao/roteiro_2026-08-08.json"))
    args = ap.parse_args()

    with open(args.json) as f:
        dados = json.load(f)
    dados["ofertas"] = processar(dados["ofertas"])
    with open(args.json, "w") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    print(f"Salvo em {args.json}")
