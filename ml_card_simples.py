#!/usr/bin/env python3
"""Gera card SIMPLES estilo afiliado (formato Herói 1): foto do produto + badge de desconto.
Todo texto (chamada, preço, link) vai na MENSAGEM do WhatsApp, não no card."""
import os, sys, json, base64, urllib.request, argparse, html as html_mod

def baixar_foto(url, destino="/tmp/ml_card_foto.png"):
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        with open(destino, "wb") as f:
            f.write(data)
        return destino
    except Exception as e:
        print(f"⚠️ Foto: {e}")
        return None

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--titulo", required=True)
    p.add_argument("--preco", type=float, default=0)
    p.add_argument("--preco-original", type=float, default=0)
    p.add_argument("--foto", default="")
    p.add_argument("--desconto", type=int, default=0)
    p.add_argument("--frete-gratis", action="store_true")
    p.add_argument("--saida", default="/home/hermes/divulgacao/card_simples.png")
    args = p.parse_args()

    foto_b64 = ""
    foto = baixar_foto(args.foto)
    if foto and os.path.exists(foto):
        with open(foto, "rb") as f:
            foto_b64 = base64.b64encode(f.read()).decode()

    desconto = args.desconto
    frete = args.frete_gratis
    titulo = html_mod.escape(args.titulo)

    badge = f'<span class="badge">-{desconto}%</span>' if desconto else ""
    frete_html = '<div class="frete-badge">🚚 FRETE GRÁTIS</div>' if frete else ""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#ffffff; }}
  .card {{
    width:1080px; height:1080px; position:relative; overflow:hidden;
    background:#ffffff; display:flex; align-items:center; justify-content:center;
  }}
  .foto {{
    width:100%; height:100%; object-fit:contain; padding:60px;
  }}
  .badge {{
    position:absolute; top:36px; right:36px; background:#e94560; color:#fff;
    font-size:64px; font-weight:800; padding:18px 36px; border-radius:20px;
    box-shadow:0 10px 30px rgba(233,69,96,.4); letter-spacing:-1px;
    font-family:'Segoe UI', system-ui, sans-serif;
  }}
  .frete-badge {{
    position:absolute; bottom:40px; left:40px; background:#1a7f3f; color:#fff;
    font-size:40px; font-weight:700; padding:14px 28px; border-radius:16px;
    font-family:'Segoe UI', system-ui, sans-serif;
    box-shadow:0 8px 24px rgba(26,127,63,.35);
  }}
</style>
</head>
<body>
  <div class="card">
    {'<img class="foto" src="data:image/png;base64,' + foto_b64 + '" alt="">' if foto_b64 else '<div style="font-size:60px">📦</div>'}
    {badge}
    {frete_html}
  </div>
</body>
</html>"""

    html_path = "/tmp/card_simples.html"
    with open(html_path, "w") as f:
        f.write(html)

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
    print(f"✅ Card simples: {args.saida}")

if __name__ == "__main__":
    main()
