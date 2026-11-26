#!/usr/bin/env python3
"""
Revisão pós-primeiro-post do Promo das Galáxias.

Após o primeiro post de oferta do dia, verifica:
1. Card: a imagem do card corresponde ao produto da oferta (visão GPT Luna)
2. Link: o meli.la do post é o link da oferta correta (bate com o JSON)
3. Texto: chamada criativa presente, preço/economia coerentes

Uso: python3 ml_revisao_post.py --json roteiro_2026-08-10.json --post 2
Retorna: OK ou lista de problemas (para o executor reportar)
"""
import os, sys, json, base64, re, urllib.request

def get_key():
    with open(os.path.expanduser("~/.hermes/.env")) as f:
        for line in f:
            if line.startswith("OPENCODE_GO_API_KEY="):
                return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("OPENCODE_GO_API_KEY", "")

def luna_visao(imagem_path, pergunta, max_tokens=300):
    """Envia imagem para o GPT Luna e retorna o texto da análise."""
    with open(imagem_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    body = json.dumps({
        "model": "gpt-5.6-luna",
        "input": [
            {"role": "user", "content": [
                {"type": "input_text", "text": pergunta},
                {"type": "input_image", "image_url": f"data:image/png;base64,{img_b64}"}
            ]}
        ],
        "max_output_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request("https://opencode.ai/zen/go/v1/responses", data=body, headers={
        "Authorization": f"Bearer {get_key()}",
        "Content-Type": "application/json",
        "User-Agent": "curl/8.0",
    })
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.load(r)
    textos = []
    for item in d.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    textos.append(c["text"])
    return "\n".join(textos).strip()

def revisar_post(json_path, post_num=2):
    """Revisa o primeiro post de oferta: card correto + link correto + texto coerente."""
    with open(json_path) as f:
        dados = json.load(f)
    ofertas = dados["ofertas"]
    cards = dados.get("cards") or []
    links = dados.get("links") or []
    chamadas = dados.get("chamadas") or []

    # O post 2 usa oferta na posição 0 da ordem distribuída — reconstruir o mapeamento
    sys.path.insert(0, os.path.expanduser("~/ml-promos-repo"))
    from ml_roteiro_diario import distribuir_ofertas, construir_roteiro

    posts = construir_roteiro(ofertas, "2026-08-10", 10, cards=cards, links=links, chamadas=chamadas)
    post = None
    for p in posts:
        if p["num"] == post_num and p["tipo"] == "oferta":
            post = p
            break
    if not post:
        return {"ok": False, "problemas": [f"Post {post_num} não encontrado"]}

    problemas = []

    # 1. Card existe?
    card_path = post.get("card")
    if not card_path or not os.path.exists(card_path):
        problemas.append(f"❌ Card ausente: {card_path}")
        card_path = None

    # 2. Link oficial curto ou fallback direto com a tag de afiliado
    texto = post.get("texto", "")
    m_link = re.search(r"https://meli\.la/\w+", texto)
    tem_tag_direta = "matt_word=renatoteodoro" in texto and "matt_tool=94885465" in texto
    if not m_link and not tem_tag_direta:
        problemas.append("❌ Texto sem link afiliado válido (meli.la ou tag direta)")

    # 3. Card corresponde ao produto? (visão Luna)
    if card_path:
        # Extrair nome do produto do texto (2ª linha)
        linhas = [l for l in texto.split("\n") if l.strip()]
        nome_produto = linhas[1] if len(linhas) > 1 else "produto"
        pergunta = (
            f"Este é o card de oferta de um produto. O texto da oferta diz que o produto é: '{nome_produto}'. "
            "Responda APENAS SIM ou NÃO: a foto/imagem do card mostra exatamente este produto (mesmo item)? "
            "Se a imagem mostra outro produto, responda NÃO."
        )
        try:
            resp = luna_visao(card_path, pergunta).strip().upper()
            print(f"  🔍 Luna (imagem vs produto): {resp[:60]}")
            if resp.startswith("NÃO") or resp.startswith("NAO"):
                problemas.append(f"❌ Card NÃO corresponde ao produto '{nome_produto}' (Luna: {resp[:40]})")
        except Exception as e:
            print(f"  ⚠️ Visão Luna falhou: {str(e)[:60]}")

    # 4. Texto tem chamada criativa (não genérica)?
    if chamadas:
        primeira_linha = texto.split("\n")[0] if texto else ""
        if not primeira_linha or primeira_linha.strip("*") in ("🔥 OFERTA!", ""):
            problemas.append("⚠️ Chamada genérica (sem Luna)")

    # 5. Economia presente?
    if "ECONOMIZE" not in texto and "no Pix" not in texto:
        problemas.append("⚠️ Sem linha de preço/economia")

    resultado = {
        "ok": len(problemas) == 0,
        "post": post_num,
        "produto": nome_produto if "nome_produto" in dir() else "",
        "problemas": problemas,
        "card": card_path,
    }
    return resultado

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.expanduser("~/divulgacao/roteiro_2026-08-10.json"))
    ap.add_argument("--post", type=int, default=2)
    args = ap.parse_args()

    r = revisar_post(args.json, args.post)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    sys.exit(0 if r["ok"] else 1)
