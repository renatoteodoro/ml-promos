#!/usr/bin/env python3
"""Gera card de anúncio profissional em HTML e renderiza para PNG via Playwright."""
import os, sys, json, base64, urllib.request, argparse, html as html_mod

def baixar_foto(url, destino="/tmp/ml_card_foto.png"):
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        # webp pode não renderizar bem — converter se possível; senão usar como está
        with open(destino, "wb") as f:
            f.write(data)
        return destino
    except Exception as e:
        print(f"⚠️ Foto: {e}")
        return None

def gerar_html(d):
    chamada = html_mod.escape(d.get("chamada", "OFERTA IMPERDÍVEL"))
    # Destacar a última palavra da chamada em vermelho (efeito <em> sem HTML cru)
    palavras = chamada.split(" ")
    if len(palavras) > 1:
        chamada_html = " ".join(palavras[:-1]) + f' <em>{palavras[-1]}</em>'
    else:
        chamada_html = f'<em>{chamada}</em>'
    titulo = html_mod.escape(d.get("titulo", ""))
    preco = d.get("preco", 0)
    original = d.get("preco_original", 0)
    desconto = d.get("desconto", 0)
    frete = d.get("frete_gratis", False)
    cupom = html_mod.escape(d.get("cupom", ""))
    link = d.get("link", "")
    foto_b64 = d.get("foto_b64", "")

    preco_fmt = f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if original and original > preco:
        orig_fmt = f"R$ {original:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        orig_fmt = ""

    # Link curto para exibição
    link_short = link
    if len(link_short) > 52:
        # Pegar a parte do produto (após /br/ e antes de ? ou /p/)
        partes = link.replace("https://www.mercadolivre.com.br/", "").split("?")[0].split("/")
        slug = partes[0][:34] if partes else link_short
        link_short = f"mercadolivre.com.br/{slug}…"

    foto_html = f'<img class="product-img" src="data:image/png;base64,{foto_b64}" alt="">' if foto_b64 else '<div class="product-img placeholder">📦</div>'

    badge = f'<span class="badge">-{desconto}%</span>' if desconto else ""
    frete_html = '<div class="frete">🚚 FRETE GRÁTIS</div>' if frete else ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Segoe UI', system-ui, sans-serif; background:#f4f1ec; }}
  .card {{
    width:1080px; height:1080px; position:relative; overflow:hidden;
    background:#ffffff; display:flex; flex-direction:column;
  }}
  /* Top accent bar */
  .topbar {{
    height:14px; background:linear-gradient(90deg,#1a1a2e 0%,#16213e 45%,#e94560 100%);
  }}
  .content {{
    flex:1; padding:48px 56px 40px; display:flex; flex-direction:column; position:relative;
  }}
  .chamada {{
    font-size:56px; font-weight:800; letter-spacing:-1.5px; line-height:1.05;
    color:#1a1a2e; text-transform:uppercase; max-width:820px;
  }}
  .chamada em {{ color:#e94560; font-style:normal; }}
  .titulo {{
    margin-top:14px; font-size:30px; font-weight:500; color:#55555f;
    line-height:1.25; max-width:860px;
  }}
  .foto-area {{
    flex:1; margin:28px 0 24px; position:relative; display:flex; align-items:center; justify-content:center;
    background:linear-gradient(180deg,#faf9f7 0%,#f1eee9 100%); border-radius:24px; overflow:hidden;
  }}
  .product-img {{ max-width:100%; max-height:100%; object-fit:contain; }}
  .placeholder {{ font-size:120px; color:#c9c4bc; }}
  .badge {{
    position:absolute; top:20px; right:20px; background:#e94560; color:#fff;
    font-size:40px; font-weight:800; padding:12px 24px; border-radius:14px;
    box-shadow:0 6px 20px rgba(233,69,96,.35); letter-spacing:-.5px;
  }}
  .preco-row {{ display:flex; align-items:baseline; gap:18px; flex-wrap:wrap; }}
  .preco-orig {{ font-size:30px; color:#9a9aa3; text-decoration:line-through; font-weight:500; }}
  .preco-now {{ font-size:88px; font-weight:800; color:#1a1a2e; letter-spacing:-2px; line-height:1; }}
  .meta-row {{ margin-top:16px; display:flex; align-items:center; gap:16px; }}
  .frete {{
    background:#e6f6ec; color:#1a7f3f; font-size:30px; font-weight:700;
    padding:10px 20px; border-radius:12px; display:inline-block;
  }}
  .cupom {{
    background:#fff3e0; color:#c2571a; font-size:30px; font-weight:700;
    padding:10px 20px; border-radius:12px; display:inline-block;
  }}
  .footer {{ margin-top:22px; display:flex; align-items:center; justify-content:space-between; gap:20px; }}
  .link {{
    font-size:24px; color:#16213e; font-weight:600; word-break:break-all; max-width:520px; line-height:1.3;
  }}
  .cta {{
    background:#e94560; color:#fff; font-size:32px; font-weight:800; letter-spacing:.3px;
    padding:18px 34px; border-radius:16px; white-space:nowrap;
    box-shadow:0 8px 24px rgba(233,69,96,.35); display:inline-block;
  }}
  .logo {{
    font-size:20px; font-weight:800; color:#e94560; letter-spacing:1px; text-transform:uppercase;
    background:#1a1a2e; color:#fff; padding:10px 16px; border-radius:10px; text-align:center;
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="topbar"></div>
    <div class="content">
      <div class="chamada">{chamada_html}</div>
      <div class="titulo">{titulo}</div>
      <div class="foto-area">
        {foto_html}
        {badge}
      </div>
      <div class="preco-row">
        {f'<span class="preco-orig">{orig_fmt}</span>' if orig_fmt else ''}
        <span class="preco-now">{preco_fmt}</span>
      </div>
      <div class="meta-row">
        {frete_html}
        {f'<span class="cupom">🎟️ {cupom}</span>' if cupom else ''}
      </div>
      <div class="footer">
        <div>
          <div class="cta">COMPRAR AGORA</div>
          <div class="link" style="margin-top:10px">🔗 {link_short}</div>
        </div>
        <div class="logo">Promo<br>das Galáxias</div>
      </div>
    </div>
  </div>
</body>
</html>"""

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--titulo", required=True)
    p.add_argument("--preco", type=float, required=True)
    p.add_argument("--preco-original", type=float, default=0)
    p.add_argument("--foto", default="")
    p.add_argument("--link", default="")
    p.add_argument("--chamada", default="OFERTA IMPERDÍVEL")
    p.add_argument("--cupom", default="")
    p.add_argument("--frete-gratis", action="store_true")
    p.add_argument("--desconto", type=int, default=0)
    p.add_argument("--saida", default="/home/hermes/divulgacao/card_pro.png")
    args = p.parse_args()

    foto_b64 = ""
    foto = baixar_foto(args.foto)
    if foto and os.path.exists(foto):
        with open(foto, "rb") as f:
            foto_b64 = base64.b64encode(f.read()).decode()

    d = {
        "chamada": args.chamada, "titulo": args.titulo,
        "preco": args.preco, "preco_original": args.preco_original,
        "desconto": args.desconto, "frete_gratis": args.frete_gratis,
        "cupom": args.cupom, "link": args.link, "foto_b64": foto_b64,
    }
    html = gerar_html(d)
    html_path = "/tmp/card_pro.html"
    with open(html_path, "w") as f:
        f.write(html)

    # Renderizar via Playwright
    import asyncio
    from playwright.async_api import async_playwright

    async def render():
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1080, "height": 1080})
            await page.goto(f"file://{html_path}")
            await page.wait_for_timeout(800)
            await page.screenshot(path=args.saida)
            await browser.close()

    asyncio.run(render())
    print(f"✅ Card profissional: {args.saida}")

if __name__ == "__main__":
    main()
