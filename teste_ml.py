#!/usr/bin/env python3
"""Teste rápido: busca ML com o token do app próprio (com permissão de busca).
Rode na SUA máquina (IP residencial).
"""
import sys, os, json, urllib.request, urllib.parse

# Token novo do app próprio — copie de ~/.hermes/mcp-tokens/mercadolibre_app.token.json (VPS)
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp-tokens", "mercadolibre_app.token.json")
if not os.path.exists(TOKEN_FILE):
    TOKEN_FILE = os.path.expanduser("~/ml-promos/mcp-tokens/mercadolibre_app.token.json")

def testar():
    with open(TOKEN_FILE) as f:
        token = json.load(f)["access_token"]
    print(f"✅ Token carregado: {token[:20]}...")
    print()

    # Teste 1: /sites/MLB/search (endpoint clássico)
    print("--- Teste 1: /sites/MLB/search ---")
    url = "https://api.mercadolibre.com/sites/MLB/search?q=cama+pet&limit=3"
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            d = json.loads(resp.read())
            print(f"✅ FUNCIONOU! {len(d.get('results', []))} resultados")
            for r in d.get("results", [])[:3]:
                print(f"  - {r.get('title','')[:55]} | R$ {r.get('price')} | {r.get('permalink','')[:60]}")
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP {e.code}: {e.read().decode()[:200]}")

    print()
    # Teste 2: /products/search (endpoint novo)
    print("--- Teste 2: /products/search ---")
    url2 = "https://api.mercadolibre.com/products/search?status=active&site_id=MLB&q=cama+pet&limit=3"
    try:
        req2 = urllib.request.Request(url2, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req2, timeout=30) as resp:
            d2 = json.loads(resp.read())
            print(f"✅ FUNCIONOU! {len(d2.get('results', []))} produtos de catálogo")
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP {e.code}: {e.read().decode()[:200]}")

    print()
    print("Se o Teste 1 funcionar, o fluxo está completo (preço + link + tag).")
    print("Se só o Teste 2 funcionar, adaptamos o script para catálogo.")

if __name__ == "__main__":
    testar()
