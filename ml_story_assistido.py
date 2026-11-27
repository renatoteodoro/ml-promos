#!/usr/bin/env python3
"""Story assistido das 12:00 — arte pronta no WhatsApp, figurinha de link no app.

A API de publicação do Instagram não aceita figurinhas em Stories (link, enquete,
localização), então nenhuma automação consegue publicar story com link clicável.
Este script faz a metade que é automatizável: escolhe a oferta do dia, monta a
arte vertical 9:16 e manda no WhatsApp do Renato com o link do grupo pronto para
colar na figurinha. Ele publica no aplicativo em segundos.

Uso:
    python3 ml_story_assistido.py             # escolhe, gera arte e manda no WhatsApp
    python3 ml_story_assistido.py --dry-run   # gera a arte e mostra, sem enviar
    python3 ml_story_assistido.py --post 5     # usa a oferta da posição 5
    python3 ml_story_assistido.py --chat 55... # envia para outro número (teste)
"""
import glob
import json
import os
import sys
import urllib.request
from datetime import datetime

DIVULGACAO = os.path.expanduser("~/divulgacao")
STATE_FILE = os.path.join(DIVULGACAO, "promo-galaxias", "insta_state.json")
BRIDGE = os.environ.get("PROMO_BRIDGE", "http://127.0.0.1:3000")
BRIDGE_TOKEN_FILE = os.path.expanduser("~/.hermes/whatsapp/session/.bridge-token")

# WhatsApp do Renato: o story vai para ele, que publica no Instagram
CHAT_PADRAO = "19331664617493@lid"
LINK_GRUPO = "https://chat.whatsapp.com/D465pHVNJpE4WRdyIzaf4m"


def bridge_headers():
    headers = {"Content-Type": "application/json"}
    try:
        with open(BRIDGE_TOKEN_FILE, encoding="utf-8") as f:
            token = f.read().strip()
    except OSError:
        token = ""
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def load_state(today=None):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
        if today is not None and state.get("date") != today:
            return {"date": today, "postados": [], "stories_postados": []}
        return state
    return {"date": today, "postados": [], "stories_postados": []}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def gerar_story_vertical(card_path):
    """Converte o card (1:1) em arte vertical 9:16 com fundo desfocado."""
    try:
        from PIL import Image, ImageFilter, ImageEnhance
        LANCZOS = getattr(Image, "Resampling", Image).LANCZOS
    except ImportError:
        print("  ⚠️ Pillow não instalado — usando o card original")
        return card_path

    im = Image.open(card_path).convert("RGB")
    w, h = im.size
    META_W, META_H = 1080, 1920

    if abs((w / h) - (9 / 16)) < 0.05:
        return card_path

    escala = min(META_W / w, META_H / h)
    novo_w, novo_h = int(w * escala), int(h * escala)
    im_red = im.resize((novo_w, novo_h), LANCZOS)

    fundo = im.resize((META_W, META_H), LANCZOS)
    fundo = fundo.filter(ImageFilter.GaussianBlur(18))
    fundo = ImageEnhance.Brightness(fundo).enhance(0.55)
    fundo.paste(im_red, ((META_W - novo_w) // 2, (META_H - novo_h) // 2))

    out_dir = os.path.join(DIVULGACAO, "promo-galaxias")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"story_assistido_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    fundo.save(out, "PNG")
    return out


def escolher_oferta(ofertas, cards, state, forcado=None):
    """Melhor oferta do dia ainda não usada no feed nem em story."""
    usados = set(state.get("postados", [])) | set(state.get("stories_postados", []))

    if forcado is not None:
        return forcado if 0 <= forcado < len(ofertas) else None

    candidatos = [
        i for i in range(min(len(ofertas), len(cards)))
        if i not in usados and cards[i] and os.path.isfile(cards[i])
    ]
    if not candidatos:
        return None

    # Prioriza frete grátis e maior desconto: o story das 12:00 é o de maior alcance
    candidatos.sort(key=lambda i: (
        not ofertas[i].get("frete_gratis", False),
        -(ofertas[i].get("desconto") or 0),
    ))
    return candidatos[0]


def enviar_whatsapp(chat, imagem, legenda):
    payload = json.dumps({
        "chatId": chat,
        "filePath": imagem,
        "mediaType": "image",
        "caption": legenda,
    }).encode()
    req = urllib.request.Request(f"{BRIDGE}/send-media", data=payload,
                                 headers=bridge_headers())
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode()


def main():
    dry_run = "--dry-run" in sys.argv
    chat = CHAT_PADRAO
    if "--chat" in sys.argv:
        chat = sys.argv[sys.argv.index("--chat") + 1]
    forcado = None
    if "--post" in sys.argv:
        forcado = int(sys.argv[sys.argv.index("--post") + 1]) - 1

    hoje = datetime.now().date().isoformat()
    json_path = os.path.join(DIVULGACAO, f"roteiro_{hoje}.json")
    if not os.path.exists(json_path):
        roteiros = sorted(glob.glob(os.path.join(DIVULGACAO, "roteiro_*.json")))
        roteiros = [r for r in roteiros if "9999" not in r]
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

    state = load_state(hoje)
    idx = escolher_oferta(ofertas, cards, state, forcado)
    if idx is None:
        print("✅ Toda a vitrine de hoje já foi usada em feed ou story")
        return 0

    oferta = ofertas[idx]
    card = cards[idx]
    titulo = (oferta.get("titulo") or "")[:60]
    preco = oferta.get("preco") or 0
    original = oferta.get("preco_original")
    desconto = oferta.get("desconto") or 0

    print(f"📌 Story assistido: {titulo}")
    print(f"   R$ {preco:.2f}" + (f" (de R$ {original:.2f}, -{desconto}%)" if original else ""))

    arte = gerar_story_vertical(card)
    print(f"   🖼️ Arte 1080x1920: {arte}")

    legenda = (
        "🎬 *Story do meio-dia pronto para subir*\n\n"
        f"{titulo}\n"
        f"R$ {preco:.2f}" + (f" (de R$ {original:.2f}, -{desconto}%)" if original else "") + "\n\n"
        "*Como publicar*\n"
        "1. Salve a imagem acima no celular\n"
        "2. Abra o Instagram, poste nos Stories\n"
        "3. Figurinhas, Link, e cole:\n"
        f"{LINK_GRUPO}\n\n"
        "A figurinha fica boa na faixa desfocada, acima ou abaixo do card."
    )

    if dry_run:
        print("\n🧪 [DRY RUN] Não enviou nada. Legenda que iria:")
        print("-" * 46)
        print(legenda)
        return 0

    resultado = enviar_whatsapp(chat, arte, legenda)
    print(f"✅ Enviado no WhatsApp: {resultado[:120]}")

    state["stories_postados"] = sorted(set(state.get("stories_postados", [])) | {idx})
    state.setdefault("assistidos", {})[hoje] = idx
    save_state(state)
    print(f"   Estado atualizado: oferta {idx} reservada (feed e story não repetem)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
