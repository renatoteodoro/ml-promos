#!/usr/bin/env python3
"""Gera chamadas criativas personalizadas por produto usando GPT Luna.
Lê o JSON de ofertas, chama o Luna em lotes e salva as chamadas no JSON.
"""
import os, sys, json, re, urllib.request, time

JSON_PATH = os.path.expanduser("~/divulgacao/roteiro_2026-08-10.json")
API_URL = "https://opencode.ai/zen/go/v1/responses"
MODEL = "gpt-5.6-luna"

def get_key():
    # Ler do .env
    with open(os.path.expanduser("~/.hermes/.env")) as f:
        for line in f:
            if line.startswith("OPENCODE_GO_API_KEY="):
                return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("OPENCODE_GO_API_KEY", "")

def chamar_luna(prompt, max_tokens=1500):
    """Chama o GPT Luna e retorna o texto."""
    key = get_key()
    body = json.dumps({
        "model": MODEL,
        "input": prompt,
        "max_output_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(API_URL, data=body, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "curl/8.0",
    })
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    textos = []
    for item in d.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    textos.append(c["text"])
    return "\n".join(textos).strip()

def main():
    with open(JSON_PATH) as f:
        dados = json.load(f)
    ofertas = dados["ofertas"]

    chamadas_existentes = dados.get("chamadas") or []
    print(f"Ofertas: {len(ofertas)} | Chamadas existentes: {len(chamadas_existentes)}")

    # Gerar em lotes de 10 produtos
    TAM = 10
    for inicio in range(0, len(ofertas), TAM):
        if inicio + TAM <= len(chamadas_existentes) and all(chamadas_existentes[inicio:inicio+TAM]):
            print(f"⏭️ Lote {inicio//TAM + 1} já tem chamadas")
            continue
        fatia = ofertas[inicio:inicio+TAM]
        desc_list = []
        for o in fatia:
            desc = o["desconto"]
            nome = o["titulo"].split(" - ")[0].split(",")[0][:45]
            frete = "com frete grátis" if o.get("frete_gratis") else ""
            desc_list.append(f"- {nome} | -{desc}% {frete}")

        prompt = f"""Você é um copywriter especialista em ofertas de afiliado do Mercado Livre para um grupo de WhatsApp chamado "Promo das Galáxias". Crie chamadas criativas (frases de impacto) para cada produto abaixo.

REGRAS:
- 1 chamada por produto, em pt-BR, com 1 emoji no início
- Curta: no máximo 7 palavras (ou 45 caracteres)
- Criativa, com gancho emocional/curiosidade/urgência — NUNCA genérica ("IMPERDÍVEL", "OFERTA ÚNICA")
- Estilo de referência: "🎯 CHEGA DE PERDER POR CAUSA DO CONTROLE", "😂 PERCA A RAIVA, NÃO A OFERTA!"
- Não citar o nome completo do produto, apenas algo relacionado
- Responda APENAS as chamadas, uma por linha, na MESMA ordem dos produtos

PRODUTOS:
{chr(10).join(desc_list)}

RESPOSTA (uma por linha):"""

        print(f"🔮 Lote {inicio//TAM + 1}: gerando {len(fatia)} chamadas com Luna...")
        resposta = chamar_luna(prompt)
        linhas = [l.strip() for l in resposta.split("\n") if l.strip()]
        print(f"    recebidas: {len(linhas)}")
        # Salvar
        for j, l in enumerate(linhas[:len(fatia)]):
            idx = inicio + j
            while len(chamadas_existentes) <= idx:
                chamadas_existentes.append(None)
            chamadas_existentes[idx] = l
        dados["chamadas"] = chamadas_existentes
        with open(JSON_PATH, "w") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1)
        print(f"    ✅ Lote salvo ({sum(1 for c in chamadas_existentes if c)}/{len(ofertas)})")
        time.sleep(2)

    print(f"\n🏁 Chamadas geradas: {sum(1 for c in chamadas_existentes if c)}/{len(ofertas)}")

if __name__ == "__main__":
    main()
