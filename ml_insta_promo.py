#!/usr/bin/env python3
"""
Publica 1 post do dia no Instagram @promodasgalaxias_oficial com a melhor oferta
do roteiro do grupo Promo das Galáxias (afiliação ML) + CTA do grupo.

Uso:
    python3 ml_insta_promo.py                  # publica a 1ª oferta não postada de hoje
    python3 ml_insta_promo.py --dry-run        # simula sem publicar
    python3 ml_insta_promo.py --post N         # publica a oferta do post N (1-102)

Anti-repetição: state em ~/divulgacao/promo-galaxias/insta_state.json
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime

DIVULGACAO = os.path.expanduser("~/divulgacao")
STATE_FILE = os.path.join(DIVULGACAO, "promo-galaxias", "insta_state.json")
PUBLISH_ENDPOINT = "http://127.0.0.1:8651/api/instagram-publish"
GRUPO_LINK = "https://chat.whatsapp.com/D465pHVNJpE4WRdyIzaf4m"

HASHTAGS = "#PromoDasGalaxias #OfertasDoDia #Promoção #MercadoLivre #Economize #Descontos #ComprasInteligentes"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"postados": []}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def publicar(image_url, caption):
    data = json.dumps({
        "image_url": image_url,
        "caption": caption,
        "account": "promo",
    }).encode()
    req = urllib.request.Request(PUBLISH_ENDPOINT, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body[:300]}")


def main():
    dry_run = "--dry-run" in sys.argv
    hoje = datetime.now().date().isoformat()
    json_path = os.path.join(DIVULGACAO, f"roteiro_{hoje}.json")

    if not os.path.exists(json_path):
        # Fallback: roteiro mais recente
        import glob
        roteiros = sorted(glob.glob(os.path.join(DIVULGACAO, "roteiro_*.json")))
        if not roteiros:
            print("❌ Nenhum roteiro encontrado")
            return 1
        json_path = roteiros[-1]
        hoje = os.path.basename(json_path).replace("roteiro_", "").replace(".json", "")
        print(f"📂 Usando roteiro de {hoje}")

    with open(json_path) as f:
        dados = json.load(f)
    ofertas = dados.get("ofertas", [])
    cards = dados.get("cards", [])
    links = dados.get("links", [])

    # Selecionar post: --post N ou primeiro não postado
    state = load_state()
    postados = set(state.get("postados", []))

    if "--post" in sys.argv:
        idx = int(sys.argv[sys.argv.index("--post") + 1]) - 1
        candidatos = [idx]
    else:
        candidatos = [i for i in range(len(ofertas)) if i not in postados]

    if not candidatos:
        print("✅ Todas as ofertas já foram postadas hoje")
        return 0

    idx = candidatos[0]
    o = ofertas[idx]
    card = cards[idx] if idx < len(cards) else None
    link = links[idx] if idx < len(links) else None

    if not card or not os.path.exists(card):
        print(f"❌ Card não encontrado: {card}")
        return 1

    # Montar caption
    nome = o["titulo"][:80]
    preco = f"R$ {o['preco']:.2f}".replace(".", ",")
    desc = o.get("desconto") or 0
    frete = "🚚 Frete grátis" if o.get("frete_gratis") else ""
    cupom = ""
    cupom_info = o.get("cupom") or {}
    if cupom_info.get("tem_cupom"):
        dc = cupom_info.get("desconto_cupom", "")
        if dc:
            cupom = f"🎟️ +{dc} com Cupom"

    caption = (
        f"🔥 OFERTA DE HOJE NA GALÁXIA!\n\n"
        f"{nome}\n\n"
        f"💰 Por {preco} no Pix"
        + (f" ({desc}% OFF)" if desc else "")
        + (f"\n{frete}" if frete else "")
        + (f"\n{cupom}" if cupom else "")
        + f"\n\n🎯 Preço comparado — o menor do catálogo!\n"
        + f"👇 Quer receber TODAS as ofertas todo dia? Comenta GRUPO que te envio o link!\n\n"
        + f"{HASHTAGS}"
    )

    print(f"📌 Postando: {nome[:60]}")
    print(f"   Preço: {preco} | Desc: {desc}% | Card: {os.path.basename(card)}")

    if dry_run:
        print(f"\n🧪 [DRY RUN] caption:\n{caption}\n")
        return 0

    # Upload da imagem para URL pública (litterbox)
    import subprocess
    r = subprocess.run(["curl", "-s", "-m", "60", "-F", "reqtype=fileupload",
                        "-F", "time=24h", "-F", f"fileToUpload=@{card}"],
                       capture_output=True, text=True,
                       check=False)
    public_url = r.stdout.strip()
    if not public_url.startswith("http"):
        print(f"❌ Upload falhou: {r.stdout[:100]}")
        return 1
    print(f"   📤 Imagem: {public_url[:60]}")

    result = publicar(public_url, caption)
    print(f"✅ PUBLICADO: {result}")

    state["postados"] = sorted(postados | {idx})
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
