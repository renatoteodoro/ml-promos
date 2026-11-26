#!/usr/bin/env python3
"""Gera arte de divulgação do Promo das Galáxias (v2) — alien em SVG (não emoji).
"""
import os, sys, argparse

ALIEN_SVG = """<svg width="200" height="180" viewBox="0 0 200 180" xmlns="http://www.w3.org/2000/svg">
  <!-- cabeça -->
  <ellipse cx="100" cy="90" rx="78" ry="72" fill="#7ec850"/>
  <ellipse cx="100" cy="90" rx="78" ry="72" fill="none" stroke="#5da53a" stroke-width="4"/>
  <!-- olhos grandes -->
  <ellipse cx="68" cy="88" rx="26" ry="30" fill="#0d1530"/>
  <ellipse cx="132" cy="88" rx="26" ry="30" fill="#0d1530"/>
  <ellipse cx="72" cy="82" rx="9" ry="10" fill="#fff"/>
  <ellipse cx="136" cy="82" rx="9" ry="10" fill="#fff"/>
  <!-- boca -->
  <path d="M 78 130 Q 100 148 122 130" stroke="#3c7a2a" stroke-width="5" fill="none" stroke-linecap="round"/>
  <!-- anteninhas -->
  <line x1="62" y1="22" x2="50" y2="4" stroke="#5da53a" stroke-width="5" stroke-linecap="round"/>
  <line x1="138" y1="22" x2="150" y2="4" stroke="#5da53a" stroke-width="5" stroke-linecap="round"/>
  <circle cx="50" cy="4" r="7" fill="#ffe066"/>
  <circle cx="150" cy="4" r="7" fill="#ffe066"/>
</svg>"""

def gerar_html(tipo):
    W, H = (1080, 1350) if tipo == "post" else (1080, 1920)
    tamanhos = {
        "post": {"alien": 200, "badge": 34, "titulo": 88, "sub": 38, "item": 34, "cta": 42, "extra": 28},
        "story": {"alien": 230, "badge": 38, "titulo": 100, "sub": 44, "item": 40, "cta": 50, "extra": 32},
    }
    T = tamanhos[tipo]

    if tipo == "post":
        chamada = 'A GALÁXIA DAS <span>OFERTAS</span>'
        subtitulo = "Ofertas reais do Mercado Livre com economia de verdade"
        cta = "ENTRAR NO GRUPO"
        extra = '<div class="extra">📱 Link do grupo nos stories e na bio</div>'
    else:
        chamada = 'OFERTAS DE <span>OUTRO PLANETA</span>'
        subtitulo = "100 ofertas por dia, até 59% OFF"
        cta = "TOQUE AQUI"
        extra = '<div class="extra">👆 Arraste para cima e entre no grupo</div>'

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Segoe UI', system-ui, sans-serif; }}
  .card {{
    width:{W}px; height:{H}px; position:relative; overflow:hidden;
    background:radial-gradient(ellipse at 30% 18%, #243b66 0%, #101b3d 50%, #060a1f 100%);
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    padding:60px 72px; text-align:center;
  }}
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
      radial-gradient(1.5px 1.5px at 85% 15%, rgba(255,255,255,.7), transparent),
      radial-gradient(2px 2px at 15% 15%, rgba(255,255,255,.8), transparent),
      radial-gradient(1px 1px at 65% 75%, rgba(255,255,255,.5), transparent);
  }}
  .planeta1 {{
    position:absolute; width:170px; height:170px; border-radius:50%;
    background:radial-gradient(circle at 35% 30%, #ffd166 0%, #e8590c 75%);
    top:7%; right:5%; box-shadow:0 0 70px rgba(232,89,12,.45);
  }}
  .planeta1::after {{
    content:''; position:absolute; top:50%; left:-14px; right:-14px; height:34px;
    background:rgba(255,209,102,.25); border-radius:50%; transform:rotate(-18deg);
  }}
  .planeta2 {{
    position:absolute; width:100px; height:100px; border-radius:50%;
    background:radial-gradient(circle at 30% 30%, #a5d8ff 0%, #1971c2 75%);
    bottom:10%; left:7%; box-shadow:0 0 50px rgba(165,216,255,.35);
  }}
  .nave {{
    position:absolute; bottom:16%; right:9%; font-size:52px;
    filter:drop-shadow(0 8px 20px rgba(255,255,255,.25));
  }}
  .alien {{ margin-bottom:14px; position:relative; z-index:2; }}
  .badge {{
    background:#e94560; color:#fff; font-size:{T['badge']}px; font-weight:800;
    padding:12px 36px; border-radius:50px; letter-spacing:.5px;
    margin-bottom:28px; display:inline-block; position:relative; z-index:2;
    box-shadow:0 8px 24px rgba(233,69,96,.4);
  }}
  .titulo {{
    font-size:{T['titulo']}px; font-weight:900;
    color:#fff; letter-spacing:-2px; line-height:1.08;
    position:relative; z-index:2;
    text-shadow:0 6px 30px rgba(0,0,0,.5);
  }}
  .titulo span {{ color:#ffe066; }}
  .subtitulo {{
    font-size:{T['sub']}px; font-weight:600;
    color:#c9d4f0; margin-top:26px; line-height:1.4;
    position:relative; z-index:2; max-width:860px;
  }}
  .divisor {{
    width:200px; height:5px; border-radius:3px;
    background:linear-gradient(90deg,#ffe066,#e94560);
    margin:32px auto; position:relative; z-index:2;
  }}
  .oferta-item {{
    font-size:{T['item']}px; font-weight:700; color:#fff;
    margin:8px 0; position:relative; z-index:2;
  }}
  .oferta-item em {{ font-style:normal; color:#ffe066; }}
  .cta {{
    background:#25d366; color:#071a0e; font-size:{T['cta']}px;
    font-weight:900; padding:22px 54px; border-radius:60px; letter-spacing:.3px;
    margin-top:{'44px' if tipo=='post' else '56px'}; position:relative; z-index:2;
    box-shadow:0 12px 40px rgba(37,211,102,.35); display:inline-block;
  }}
  .cta small {{ display:block; font-size:24px; font-weight:600; margin-top:6px; opacity:.85; }}
  .extra {{
    font-size:{T['extra']}px; color:#8fa0c8; margin-top:24px; position:relative; z-index:2;
  }}
  .footer-logo {{
    position:absolute; bottom:32px; width:100%; text-align:center;
    color:#5c6fa3; font-size:24px; font-weight:700; letter-spacing:3px;
    z-index:2; text-transform:uppercase;
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="stars"></div>
    <div class="planeta1"></div>
    <div class="planeta2"></div>
    <div class="nave">🛸</div>
    <div class="alien">{ALIEN_SVG}</div>
    <div class="badge">💸 ATÉ 59% OFF</div>
    <div class="titulo">{chamada}</div>
    <div class="subtitulo">{subtitulo}</div>
    <div class="divisor"></div>
    <div class="oferta-item">🚀 <em>100 ofertas</em> por dia</div>
    <div class="oferta-item">🕐 Das <em>08h às 21h54</em></div>
    <div class="oferta-item">🚚 <em>Fretes grátis</em> inclusos</div>
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

    html = gerar_html(args.tipo)
    path = "/tmp/insta_art2.html"
    with open(path, "w") as f:
        f.write(html)

    import asyncio
    from playwright.async_api import async_playwright

    saida = args.saida or f"/home/hermes/divulgacao/insta_{args.tipo}_v2.png"
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
    print(f"✅ Arte {args.tipo} v2: {saida}")

if __name__ == "__main__":
    main()
