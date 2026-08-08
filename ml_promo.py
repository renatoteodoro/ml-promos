#!/usr/bin/env python3
"""
Busca de promoções Mercado Livre + link de afiliado + envio automático ao JARVIS.
Método: extrai ofertas do SITE do ML (página /ofertas e busca) — funciona sem
token e sem restrição de IP (diferente da API).

Windows:  python ml_promo.py
Linux:    python3 ml_promo.py

Requisitos: Python 3 — sem dependências externas.
"""
import sys, os, json, re, html, time, hmac, hashlib, argparse, urllib.request, urllib.parse

# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÃO (edite aqui)
# ─────────────────────────────────────────────────────────────
# ⚠️ SUA TAG DE AFILIADO — pegue no painel https://afiliados.mercadolivre.com.br
AFF_TAG = "matt:renatoteodoro:94885465"

# Nichos padrão (usado se você não passar --nicho)
NICHOS_PADRAO = "cama pet;ração pet;brinquedo pet;comedouro pet;arranhador;casinha pet"

# Webhook do JARVIS
WEBHOOK_URL = "https://webhook.techteo.com.br/webhooks/ml-promos"
WEBHOOK_SECRET = "mlpromos-secret-2026"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
# ─────────────────────────────────────────────────────────────

def baixar(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def extrair_ofertas_html(page_url):
    """Extrai ofertas (título + preço + link /p/MLB) do HTML do site ML."""
    c = baixar(page_url)
    cards = []
    partes = c.split('poly-card poly-card--')
    for p in partes[1:]:
        m_link = re.search(r'href="(https://www\.mercadolivre\.com\.br/[^"]*/p/MLB\d+[^"]*)"', p)
        m_title = re.search(r'poly-component__title-wrapper"><a[^>]*>(.*?)</a>', p, re.S)
        m_price = re.search(r'andes-money-amount__fraction[^>]*>([^<]+)<', p)
        m_disc = re.search(r'(\d+)% OFF', p)
        m_old = re.search(r'aria-label="Antes:\s*([0-9.]+)\s*reais"', p)
        m_img = re.search(r'<img[^>]+src="([^"]+)"', p)
        m_free = 'free_shipping' in p or 'FRETE GRÁTIS' in p or 'Frete grátis' in p
        if m_link and m_title and m_price:
            preco = float(m_price.group(1).replace(".", "").replace(",", "."))
            cards.append({
                "titulo": html.unescape(m_title.group(1)).strip(),
                "preco": preco,
                "preco_original": float(m_old.group(1).replace(".", "")) if m_old else 0,
                "desconto": int(m_disc.group(1)) if m_disc else 0,
                "frete_gratis": m_free,
                "link": m_link.group(1).split("?")[0],
                "imagem": m_img.group(1) if m_img else "",
            })
    return cards

def buscar_nicho(nicho, limite=6):
    """Busca ofertas por nicho filtrando a página de ofertas do dia por palavra-chave."""
    try:
        ofertas = extrair_ofertas_html("https://www.mercadolivre.com.br/ofertas")
        # Filtrar por palavra-chave do nicho no título
        palavras = [w for w in nicho.lower().split() if len(w) > 2]
        filtradas = []
        for o in ofertas:
            t = o["titulo"].lower()
            if any(p in t for p in palavras):
                filtradas.append(o)
        return filtradas[:limite]
    except Exception as e:
        print(f"⚠️ Erro em '{nicho}': {e}")
        return []

def link_afiliado(permalink):
    sep = "&" if "?" in permalink else "?"
    return f"{permalink}{sep}matt_word=renatoteodoro&matt_tool=94885465"

def enviar_webhook(ofertas):
    """Envia as ofertas ao JARVIS via webhook com assinatura HMAC V2."""
    payload = json.dumps({"ofertas": ofertas, "gerado_em": time.strftime("%Y-%m-%d %H:%M")}).encode()
    ts = str(int(time.time()))
    signature = hmac.new(WEBHOOK_SECRET.encode(), ts.encode() + b"." + payload, hashlib.sha256).hexdigest()
    req = urllib.request.Request(WEBHOOK_URL, data=payload, headers={
        "Content-Type": "application/json",
        "X-Webhook-Signature-V2": signature,
        "X-Webhook-Timestamp": ts,
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"✅ Enviado ao JARVIS! HTTP {resp.status}")
            return True
    except urllib.error.HTTPError as e:
        print(f"⚠️ Webhook: HTTP {e.code}: {e.read().decode()[:200]}")
        return False
    except Exception as e:
        print(f"⚠️ Webhook: {e}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nicho", default=NICHOS_PADRAO, help="nichos separados por ;")
    parser.add_argument("--limite", type=int, default=6)
    parser.add_argument("--desconto", type=int, default=0, help="desconto mínimo %")
    parser.add_argument("--frete-gratis", action="store_true")
    parser.add_argument("--ofertas-do-dia", action="store_true", help="usa a página de ofertas do dia")
    args = parser.parse_args()

    todos = []
    if args.ofertas_do_dia:
        print("🔍 Buscando ofertas do dia...")
        todos = extrair_ofertas_html("https://www.mercadolivre.com.br/ofertas")[:args.limite]
    else:
        for nicho in [n.strip() for n in args.nicho.split(";") if n.strip()]:
            print(f"🔍 Buscando: {nicho}...")
            itens = buscar_nicho(nicho, args.limite)
            for p in itens:
                if args.desconto and p["desconto"] < args.desconto:
                    continue
                if args.frete_gratis and not p["frete_gratis"]:
                    continue
                p["link"] = link_afiliado(p["link"])
                p["nicho"] = nicho
                todos.append(p)

    if not todos:
        print("Nenhuma oferta encontrada com os filtros.")
        return

    print(f"\n✅ {len(todos)} ofertas encontradas — enviando ao JARVIS...")
    enviar_webhook(todos[:10])

    # Backup local
    pasta = os.path.expanduser("~/ml-promos")
    os.makedirs(pasta, exist_ok=True)
    with open(os.path.join(pasta, f"ofertas-{time.strftime('%Y%m%d-%H%M')}.json"), "w") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)
    print(f"💾 Backup salvo em {pasta}")

if __name__ == "__main__":
    main()
