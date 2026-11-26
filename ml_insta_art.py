#!/usr/bin/env python3
"""Gera arte de divulgação do Promo das Galáxias para Instagram (post + story).
Tema: alien verde 👽 + galáxia + ofertas ML.
"""
import os, sys, argparse

def gerar_html(tipo, chamada, subtitulo, cta, extra=""):
    if tipo == "post":
        W, H = 1080, 1350
    else:
        W, H = 1080, 1920

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Segoe UI', system-ui, sans-serif; }}
  .card {{
    width:{W}px; height:{H}px; position:relative; overflow:hidden;
    background:radial-gradient(ellipse at 30% 20%, #1b2a4a 0%, #0d1530 55%, #05081a 100%);
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    padding:60px 72px; text-align:center;
  }}
  /* Estrelas */
  .stars {{
    position:absolute; inset:0; pointer-events:none;
    background-image:
      radial-gradient(2px 2px at 20% 30%, rgba(255,255,255,.9), transparent),
      radial-gradient(1.5px 1.5px at 40% 70%, rgba(255,255,255,.7), transparent),
      radial-gradient(2.5px 2.5px at 60% 20%, rgba(255,255,255,.8), transparent),
      radial-gradient(1px 1px at 80% 50%, rgba(255,255,255,.6), transparent),
      radial-gradient(2px 2px at 90% 80%, rgba(255,255,255,.8), transparent),
      radial-gradient(1.5px 1.5px at 10% 60%, rgba(255,255,255,.6), transparent),
      radial-gradient(2px 2px at 50% 90%, rgba(255,255,255,.7), transparent),
      radial-gradient(1px 1px at 70% 40%, rgba(255,255,255,.9), transparent),
      radial-gradient(2px 2px at 30% 85%, rgba(255,255,255,.5), transparent),
      radial-gradient(1.5px 1.5px at 85% 15%, rgba(255,255,255,.7), transparent);
  }}
  /* Planetas decorativos */
  .planeta1 {{ position:absolute; width:160px; height:160px; border-radius:50%;
    background:radial-gradient(circle at 35% 30%, #ffd166, #e8590c 70%);
    top:8%; right:6%; box-shadow:0 0 60px rgba(232,89,12,.4); }}
  .planeta2 {{ position:absolute; width:90px; height:90px; border-radius:50%;
    background:radial-gradient(circle at 30% 30%, #74c0fc, #1864ab 70%);
    bottom:12%; left:8%; box-shadow:0 0 40px rgba(116,192,252,.35); }}
  .alien {{
    font-size:150px; line-height:1; margin-bottom:20px;
    filter:drop-shadow(0 12px 30px rgba(0,0,0,.5));
    position:relative; z-index:2;
  }}
  .badge {{
    background:#e94560; color:#fff; font-size:34px; font-weight:800;
    padding:12px 34px; border-radius:50px; letter-spacing:.5px;
    margin-bottom:30px; display:inline-block; position:relative; z-index:2;
    box-shadow:0 8px 24px rgba(233,69,96,.4);
  }}
  .titulo {{
    font-size:{'92px' if tipo=='post' else '110px'}; font-weight:900;
    color:#fff; letter-spacing:-2px; line-height:1.05;
    position:relative; z-index:2;
    text-shadow:0 6px 30px rgba(0,0,0,.5);
  }}
  .titulo span {{ color:#ffe066; }}
  .subtitulo {{
    font-size:{'40px' if tipo=='post' else '46px'}; font-weight:600;
    color:#c9d4f0; margin-top:28px; line-height:1.4;
    position:relative; z-index:2; max-width:850px;
  }}
  .divisor {{
    width:200px; height:5px; border-radius:3px;
    background:linear-gradient(90deg,#ffe066,#e94560);
    margin:36px auto; position:relative; z-index:2;
  }}
  .oferta-item {{
    font-size:{'36px' if tipo=='post' else '42px'}; font-weight:700; color:#fff;
    margin:10px 0; position:relative; z-index:2;
  }}
  .oferta-item em {{ font-style:normal; color:#ffe066; }}
  .cta {{
    background:#25d366; color:#071a0e; font-size:{'44px' if tipo=='post' else '52px'};
    font-weight:900; padding:24px 56px; border-radius:60px; letter-spacing:.3px;
    margin-top:{'48px' if tipo=='post' else '60px'}; position:relative; z-index:2;
    box-shadow:0 12px 40px rgba(37,211,102,.35); display:inline-block;
  }}
  .cta small {{ display:block; font-size:26px; font-weight:600; margin-top:6px; opacity:.85; }}
  .extra {{
    font-size:26px; color:#8fa0c8; margin-top:26px; position:relative; z-index:2;
  }}
  .footer-logo {{
    position:absolute; bottom:34px; width:100%; text-align:center;
    color:#5c6fa3; font-size:24px; font-weight:700; letter-spacing:2px;
    z-index:2; text-transform:uppercase;
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="stars"></div>
    <div class="planeta1"></div>
    <div class="planeta2"></div>
    <div class="alien">👽</div>
    <div class="badge">💸 ATÉ 59% OFF</div>
    <div class="titulo">{chamada}</div>
    <div class="subtitulo">{subtitulo}</div>
    <div class="divisor"></div>
    <div class="oferta-item">🚀 <em>100 ofertas</em> por dia</div>
    <div class="oferta-item">🕐 <em>08h às 21h54</em></div>
    <div class="oferta-item">🚚 <em>Fretes grátis</em></div>
    {extra}
    <div class="cta">{cta}<small>É grátis! 😉</small></div>
    <div class="footer-logo">Promo das Galáxias</div>
  </div>
</body>
</html>"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tipo", choices=["post", "story"], default="post")
    ap.add_argument("--saida", default="")
    args = ap.parse_args()

    if args.tipo == "post":
        chamada = "A GALÁXIA DAS <span>OFERTAS</span>"
        subtitulo = "Ofertas reais do Mercado Livre com economia de verdade"
        cta = "ENTRAR NO GRUPO"
        extra = '<div class="extra">📱 Link do grupo nos stories e no link da bio</div>'
    else:
        chamada = "OFERTAS DE <span>OUTRO PLANETA</span>"
        subtitulo = "100 ofertas por dia, até 59% OFF"
        cta = "TOQUE AQUI"
        extra = '<div class="extra">👆 Arraste para o link do grupo</div>'

    html = gerar_html(args.tipo, chamada, subtitulo, cta, extra)
    path = "/tmp/insta_art.html"
    with open(path, "w") as f:
        f.write(html)

    import asyncio
    from playwright.async_api import async_playwright

    saida = args.saida or f"/home/hermes/divulgacao/insta_{args.tipo}.png"
    W, H = (1080, 1350) if args.tipo == "post" else (1080, 1920)

    async def render():
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": W, "height": H})
            await page.goto(f"file://{path}")
            await page.wait_for_timeout(600)
            await page.screenshot(path=saida)
            await browser.close()

    asyncio.run(render())
    print(f"✅ Arte {args.tipo}: {saida}")

if __name__ == "__main__":
    main()
