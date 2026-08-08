#!/usr/bin/env python3
"""
Gerador de card de anúncio para afiliados do Mercado Livre.
Estilo: "promo de afiliado" (chamada + foto + preço + desconto + link).

Uso:
  python3 ml_card.py --titulo "Aparador Philips Multigroom" \
      --preco 118 --preco-original 249 --foto URL --link URL \
      --cupom "PROMO15" --chamada "ESSA FAZ TUDO QUE VOCÊ PRECISA" \
      --saida card.jpg

Requisitos: pip install pillow requests
"""
import os, sys, argparse, urllib.request
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
def font(size, bold=False):
    nome = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    path = os.path.join(FONT_DIR, nome)
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def baixar_foto(url, destino="/tmp/ml_card_foto.jpg"):
    """Baixa a foto do produto."""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            with open(destino, "wb") as f:
                f.write(resp.read())
        return destino
    except Exception as e:
        print(f"⚠️ Foto: {e}")
        return None

def gerar_card(titulo, preco, preco_original, foto_url, link,
               chamada="", cupom="", frete_gratis=False, desconto=0,
               saida="/home/hermes/divulgacao/card_afiliado.jpg"):
    W, H = 1080, 1080
    card = Image.new('RGB', (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(card)

    # Fundo gradiente verde-menta (estilo Philips)
    for y in range(H):
        r = int(185 + (205-185) * y / H)
        g = int(235 + (245-235) * y / H)
        b = int(215 + (225-215) * y / H)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    font_call = font(50, bold=True)
    font_title = font(38)
    font_small = font(40)
    font_price = font(92, bold=True)
    font_coupon = font(40, bold=True)
    font_link = font(34)

    # Chamada
    texto = chamada or "OFERTA IMPERDÍVEL"
    tw = draw.textlength(texto, font=font_call)
    draw.text(((W-tw)/2, 30), texto, fill=(17, 24, 39), font=font_call)

    # Título (quebrado em até 2 linhas)
    tw2 = draw.textlength(titulo, font=font_title)
    if tw2 > W - 80:
        titulo = titulo[:45] + "..."
    tw2 = draw.textlength(titulo, font=font_title)
    draw.text(((W-tw2)/2, 95), titulo, fill=(60, 70, 80), font=font_title)

    # Foto (grande, ocupando o centro — elemento principal do anúncio)
    foto = baixar_foto(foto_url)
    if foto and os.path.exists(foto):
        try:
            im = Image.open(foto).convert("RGB")
            im.thumbnail((860, 520), Image.LANCZOS)
            offset_x = (W - im.width) // 2
            offset_y = 170 + (520 - im.height) // 2
            card.paste(im, (offset_x, offset_y))
        except Exception as e:
            print(f"⚠️ Erro ao processar foto: {e}")
    else:
        draw.rectangle([90, 170, 990, 690], fill=(255,255,255), outline=(200,200,200), width=3)
        draw.text((480, 380), "📦", fill=(100, 180, 140), font=font(130))
        draw.text((400, 530), "[ foto indisponível ]", fill=(150,150,150), font=font_small)

    # Preço
    y = 700
    if preco_original and preco_original > preco:
        t3 = f"De R$ {preco_original:.2f}".replace(".", ",")
        tw3 = draw.textlength(t3, font=font_small)
        draw.text(((W-tw3)/2, y), t3, fill=(120, 80, 80), font=font_small)
        y += 48

    t4 = f"R$ {preco:.2f}".replace(".", ",")
    if desconto:
        t4 += f"  (-{desconto}%)"
    tw4 = draw.textlength(t4, font=font_price)
    draw.text(((W-tw4)/2, y), t4, fill=(17, 24, 39), font=font_price)

    # Frete grátis
    if frete_gratis:
        t5 = "🚚 FRETE GRÁTIS"
        tw5 = draw.textlength(t5, font=font_coupon)
        draw.text(((W-tw5)/2, y + 95), t5, fill=(20, 130, 80), font=font_coupon)
        y += 55

    # Cupom
    if cupom:
        t6 = f"🎟️ Cupom: {cupom}"
        tw6 = draw.textlength(t6, font=font_coupon)
        draw.text(((W-tw6)/2, y + 100), t6, fill=(200, 60, 60), font=font_coupon)
        y += 55

    # Link
    t7 = f"🔗 {link}" if link else "🔗 Clique e aproveite!"
    tw7 = draw.textlength(t7, font=font_link)
    if tw7 > W - 60:
        t7 = t7[:50] + "..."
        tw7 = draw.textlength(t7, font=font_link)
    draw.text(((W-tw7)/2, y + 140), t7, fill=(40, 90, 150), font=font_link)

    os.makedirs(os.path.dirname(saida), exist_ok=True)
    card.save(saida, quality=94)
    print(f"✅ Card gerado: {saida}")
    return saida

def main():
    p = argparse.ArgumentParser(description="Gera card de anúncio afiliado ML")
    p.add_argument("--titulo", required=True)
    p.add_argument("--preco", type=float, required=True)
    p.add_argument("--preco-original", type=float, default=0)
    p.add_argument("--foto", default="")
    p.add_argument("--link", default="")
    p.add_argument("--chamada", default="")
    p.add_argument("--cupom", default="")
    p.add_argument("--frete-gratis", action="store_true")
    p.add_argument("--desconto", type=int, default=0)
    p.add_argument("--saida", default="/home/hermes/divulgacao/card_afiliado.jpg")
    args = p.parse_args()

    gerar_card(args.titulo, args.preco, args.preco_original, args.foto, args.link,
               args.chamada, args.cupom, args.frete_gratis, args.desconto, args.saida)

if __name__ == "__main__":
    main()
