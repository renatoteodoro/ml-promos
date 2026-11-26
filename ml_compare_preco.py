#!/usr/bin/env python3
"""
Comparação de preços entre anúncios do MESMO produto (catálogo ML).

Para cada produto de catálogo (/p/MLB...), o ML tem vários vendedores (items).
Este módulo busca TODOS os vendedores e encontra o MENOR preço + frete grátis,
para divulgar sempre a melhor oferta possível.

API: GET /products/{id}/items?limit=50 (token do app "Promo das Galáxias")
"""
import os, json, time, urllib.request, re, subprocess, sys

TOKEN_PATH = os.path.expanduser("~/.hermes/mcp-tokens/mercadolibre_app.token.json")
REFRESH_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml_refresh_token.py")

def get_token():
    """Retorna o token, renovando automaticamente se expirado ou perto de expirar."""
    # Verificar tempo restante
    try:
        with open(TOKEN_PATH) as f:
            tok = json.load(f)
        exp = tok.get("expires_at") or tok.get("created_at", 0) + tok.get("expires_in", 21600)
        restante = exp - time.time()
        if restante < 3600:  # < 1h → renovar
            print("  🔄 Token expirando, renovando automaticamente...")
            subprocess.run([sys.executable, REFRESH_SCRIPT, "--force"], capture_output=True)
    except Exception:
        pass
    with open(TOKEN_PATH) as f:
        return json.load(f)["access_token"]

def extrair_mlb_id(link):
    """Extrai o MLB id do link do produto (/p/MLB...)."""
    m = re.search(r"/p/(MLB\d+)", link)
    return m.group(1) if m else None

def buscar_melhor_preco(mlb_id, limite=50):
    """
    Busca todos os vendedores do produto e retorna o melhor (menor preço).
    Retorna dict com item_id, price, original_price, free_shipping, total_vendedores.
    """
    token = get_token()
    url = f"https://api.mercadolibre.com/products/{mlb_id}/items?limit={limite}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.load(r)
    except Exception as e:
        return None

    results = d.get("results", [])
    if not results:
        return None

    # Melhor = menor preço (empate: frete grátis)
    melhor = None
    for it in results:
        preco = it.get("price") or 0
        if preco <= 0:
            continue
        free = bool((it.get("shipping") or {}).get("free_shipping"))
        candidato = {
            "item_id": it.get("item_id"),
            "price": preco,
            "original_price": it.get("original_price") or 0,
            "free_shipping": free,
            "seller_id": it.get("seller_id"),
            "total_vendedores": len(results),
        }
        if melhor is None:
            melhor = candidato
        else:
            if preco < melhor["price"]:
                melhor = candidato
            elif preco == melhor["price"] and free and not melhor["free_shipping"]:
                melhor = candidato
    return melhor

def enriquecer_oferta(oferta):
    """Dado uma oferta do /ofertas, enriquece com o menor preço do catálogo."""
    mlb_id = extrair_mlb_id(oferta.get("link", ""))
    if not mlb_id:
        return oferta
    melhor = buscar_melhor_preco(mlb_id)
    if not melhor:
        return oferta

    # Se o menor preço for MELHOR que o do card, atualizar
    if melhor["price"] < oferta.get("preco", 0):
        oferta["preco"] = melhor["price"]
        oferta["preco_original"] = melhor["original_price"] or oferta.get("preco_original", 0)
        oferta["frete_gratis"] = melhor["free_shipping"] or oferta.get("frete_gratis", False)
        # Recalcular desconto
        if oferta["preco_original"] > oferta["preco"]:
            oferta["desconto"] = round((1 - oferta["preco"] / oferta["preco_original"]) * 100)
        oferta["menor_preco_catalogo"] = True
        oferta["total_vendedores"] = melhor["total_vendedores"]
    return oferta

def enriquecer_lote(ofertas, max_por_vez=40):
    """Enriquece um lote de ofertas com o menor preço do catálogo."""
    enriquecidas = []
    melhoradas = 0
    for i, o in enumerate(ofertas):
        r = enriquecer_oferta(o)
        if r.get("menor_preco_catalogo"):
            melhoradas += 1
        enriquecidas.append(r)
        if (i + 1) % 10 == 0:
            print(f"    ...{i+1}/{len(ofertas)} comparadas ({melhoradas} com preço melhor)")
        time.sleep(0.3)
    print(f"  ✅ {melhoradas}/{len(ofertas)} ofertas tinham preço melhor no catálogo")
    return enriquecidas

if __name__ == "__main__":
    # Teste com o controle PS5
    melhor = buscar_melhor_preco("MLB28083897")
    if melhor:
        print(f"Melhor preço PS5: R$ {melhor['price']:.2f} | frete grátis: {melhor['free_shipping']} | {melhor['total_vendedores']} vendedores")
