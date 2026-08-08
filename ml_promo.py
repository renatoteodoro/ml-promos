#!/usr/bin/env python3
"""
Busca de promoções Mercado Livre + link de afiliado + envio automático ao JARVIS.
RODAR NA MÁQUINA LOCAL (IP residencial) — a API bloqueia IP de datacenter.

Windows:  python ml_promo.py --nicho "cama pet" --desconto 15
Linux:    python3 ml_promo.py --nicho "cama pet" --desconto 15

Requisitos: Python 3 instalado (https://python.org) — sem dependências externas.
"""
import sys, os, json, time, hmac, hashlib, argparse, urllib.request, urllib.parse

# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÃO (edite aqui)
# ─────────────────────────────────────────────────────────────
# ⚠️ SUA TAG DE AFILIADO — pegue no painel https://afiliados.mercadolivre.com.br
# Gere um link de afiliado e copie o formato:
#   Se o link tiver "matt_word=X&matt_tool=Y" → tag = "matt:X:Y"
#   Se o link tiver "tag=X-20"               → tag = "X-20"
AFF_TAG = "matt:renatoteodoro:94885465"

# Nichos padrão (usado se você não passar --nicho)
NICHOS_PADRAO = "cama pet;ração pet;brinquedo pet;comedouro pet;arranhador;casinha pet"

# Webhook do JARVIS
WEBHOOK_URL = "https://webhook.techteo.com.br/webhooks/ml-promos"
WEBHOOK_SECRET = "mlpromos-secret-2026"
# ─────────────────────────────────────────────────────────────

def get_token():
    """Lê o token do ML. Procura em vários locais (Windows e Linux)."""
    candidatos = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp-tokens", "mercadolibre.token.json"),
        os.path.expanduser("~/ml-promos/mcp-tokens/mercadolibre.token.json"),
        os.path.expanduser("~/.hermes/mcp-tokens/mercadolibre.token.json"),
    ]
    for path in candidatos:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)["access_token"]
    print("❌ Token não encontrado!")
    print("   Procurei em:")
    for path in candidatos:
        print(f"   - {path}")
    print("   Copie a pasta 'mcp-tokens' para junto deste script (mesma pasta).")
    sys.exit(1)

def buscar(query, limite=6):
    token = get_token()
    params = {"q": query, "limit": limite, "status": "active"}
    url = "https://api.mercadolibre.com/sites/MLB/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    resultados = []
    for item in data.get("results", []):
        shipping = item.get("shipping", {})
        original = item.get("original_price")
        price = item.get("price")
        desconto = 0
        if original and price:
            desconto = round((1 - price / original) * 100)
        resultados.append({
            "titulo": item.get("title"),
            "preco": price,
            "preco_original": original,
            "desconto": desconto,
            "frete_gratis": shipping.get("free_shipping", False),
            "rating": item.get("average_rating"),
            "link": item.get("permalink"),
            "imagem": item.get("thumbnail"),
            "loja": item.get("official_store_name"),
        })
    return resultados

def link_afiliado(permalink):
    sep = "&" if "?" in permalink else "?"
    if AFF_TAG and "COLE" not in AFF_TAG:
        return f"{permalink}{sep}matt_word={AFF_TAG}"
    return permalink

def enviar_webhook(ofertas):
    """Envia as ofertas ao JARVIS via webhook com assinatura HMAC V2 (com timestamp)."""
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
    parser.add_argument("--nicho", default=NICHOS_PADRAO,
                        help="nichos separados por ; (ex: 'cama pet;ração')")
    parser.add_argument("--limite", type=int, default=6)
    parser.add_argument("--desconto", type=int, default=0, help="desconto mínimo %")
    parser.add_argument("--frete-gratis", action="store_true")
    args = parser.parse_args()

    todos = []
    for nicho in [n.strip() for n in args.nicho.split(";") if n.strip()]:
        print(f"🔍 Buscando: {nicho}...")
        try:
            itens = buscar(nicho, args.limite)
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print("❌ 403 — IP bloqueado. Rode NA SUA MÁQUINA (IP residencial), não na VPS.")
                sys.exit(1)
            print(f"❌ Erro {e.code} em '{nicho}'")
            continue
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

    # Salvar backup local
    pasta = os.path.expanduser("~/ml-promos")
    os.makedirs(pasta, exist_ok=True)
    with open(os.path.join(pasta, f"ofertas-{time.strftime('%Y%m%d-%H%M')}.json"), "w") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)
    print(f"💾 Backup salvo em {pasta}")

if __name__ == "__main__":
    main()
