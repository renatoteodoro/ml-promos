#!/usr/bin/env python3
"""
Publica 1 Story no Instagram @promodasgalaxias_oficial com a melhor oferta
do roteiro do dia (afiliação ML). Stories são imagens verticais (9:16).

Uso:
    python3 ml_insta_story.py            # publica a 1ª oferta não postada hoje (feed/story state)
    python3 ml_insta_story.py --dry-run  # simula sem publicar
    python3 ml_insta_story.py --post N   # publica a oferta do post N

Anti-repetição: state em ~/divulgacao/promo-galaxias/insta_state.json (campo stories_postados)
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime

DIVULGACAO = os.path.expanduser("~/divulgacao")
STATE_FILE = os.path.join(DIVULGACAO, "promo-galaxias", "insta_state.json")
STORY_ENDPOINT = "http://127.0.0.1:8651/api/instagram-story"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"postados": [], "stories_postados": []}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def gerar_story_vertical(card_path):
    """
    Converte o card do feed (4:5 ou 1:1) para formato vertical 9:16 para Stories.
    Recorte central + fundo que preenche as bordas (evita corte de texto).
    Salva em ~/divulgacao/promo-galaxias/story_{timestamp}.png
    """
    try:
        from PIL import Image, ImageFilter, ImageEnhance
        LANCZOS = getattr(Image, "Resampling", Image).LANCZOS
    except ImportError:
        print("  ⚠️ Pillow não instalado — usando card original (IG corta para 9:16)")
        return card_path

    im = Image.open(card_path).convert("RGB")
    w, h = im.size

    # Meta 9:16 (1080x1920)
    META_W, META_H = 1080, 1920

    # Se já for vertical 9:16 (±10%), usar direto
    if abs((w / h) - (9 / 16)) < 0.05:
        return card_path

    # Escalar para caber em 1080x1920 mantendo proporção
    escala = min(META_W / w, META_H / h)
    novo_w, novo_h = int(w * escala), int(h * escala)
    im_red = im.resize((novo_w, novo_h), LANCZOS)

    # Fundo: versão desfocada e escurecida preenchendo todo o canvas
    fundo = im.resize((META_W, META_H), LANCZOS)
    fundo = fundo.filter(ImageFilter.GaussianBlur(18))
    fundo = ImageEnhance.Brightness(fundo).enhance(0.55)

    # Centralizar a imagem nítida sobre o fundo
    x = (META_W - novo_w) // 2
    y = (META_H - novo_h) // 2
    fundo.paste(im_red, (x, y))

    # Salvar
    out_dir = os.path.join(DIVULGACAO, "promo-galaxias")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"story_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    fundo.save(out, "PNG")
    print(f"   📐 Story vertical 9:16 gerado: {os.path.basename(out)}")
    return out


def publicar_story(image_url):
    data = json.dumps({"image_url": image_url, "account": "promo"}).encode()
    req = urllib.request.Request(STORY_ENDPOINT, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode()


def main():
    dry_run = "--dry-run" in sys.argv
    hoje = datetime.now().date().isoformat()
    json_path = os.path.join(DIVULGACAO, f"roteiro_{hoje}.json")

    if not os.path.exists(json_path):
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

    # Selecionar: --post N ou primeira oferta com card não usada em story
    state = load_state()
    stories = set(state.get("stories_postados", []))

    if "--post" in sys.argv:
        idx = int(sys.argv[sys.argv.index("--post") + 1]) - 1
        candidatos = [idx]
    else:
        # Não repetir oferta já usada no FEED de hoje (postados) nem em story
        excluir = set(state.get("postados", [])) | stories
        candidatos = [i for i in range(len(ofertas)) if i not in excluir]

    if not candidatos:
        print("✅ Todas as ofertas já foram usadas em feed/story hoje")
        return 0

    idx = candidatos[0]
    o = ofertas[idx]
    card = cards[idx] if idx < len(cards) else None

    if not card or not os.path.exists(card):
        print(f"❌ Card não encontrado: {card}")
        return 1

    # Stories: usar o card convertido para vertical 9:16 (texto preservado, fundo desfocado)
    print(f"📌 Story: {o['titulo'][:60]}")
    print(f"   Preço: R$ {o['preco']:.2f} | Card: {os.path.basename(card)}")

    if dry_run:
        print(f"\n🧪 [DRY RUN] Publicaria story com imagem: {card}")
        return 0

    # Converter para 9:16
    card_story = gerar_story_vertical(card)

    # Upload da imagem para URL pública (litterbox)
    import subprocess
    r = subprocess.run(["curl", "-s", "-m", "60", "-F", "reqtype=fileupload",
                        "-F", "time=24h", "-F", f"fileToUpload=@{card_story}"],
                       capture_output=True, text=True, check=False)
    public_url = r.stdout.strip()
    if not public_url.startswith("http"):
        print(f"❌ Upload falhou: {r.stdout[:100]}")
        return 1
    print(f"   📤 Imagem: {public_url[:60]}")

    result = publicar_story(public_url)
    print(f"✅ STORY PUBLICADO: {result}")

    state["stories_postados"] = sorted(stories | {idx})
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
