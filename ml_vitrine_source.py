"""Fonte de contingencia: vitrine do perfil social do afiliado.

Quando a API do Mercado Livre e a pagina /ofertas passam a bloquear o IP da VPS
(HTTP 403 PA_UNAUTHORIZED_RESULT_FROM_POLICIES nos endpoints de produto e preco,
e /gz/account-verification nas paginas HTML), a vitrine /social/<tag> continua
respondendo: ela e a montra do proprio afiliado e mostra preco atual, preco
original, desconto no Pix e frete gratis de cada produto.

A vitrine so abre com os produtos quando a entrada e um link meli.la ja gerado
(a URL direta /social/<tag> cai em /lists e aparece vazia). Por isso os links
meli.la sao colhidos dos roteiros anteriores em ~/divulgacao/roteiro_*.json.

Uso:
    from ml_vitrine_source import buscar_ofertas_vitrine
    ofertas = buscar_ofertas_vitrine("/home/hermes/divulgacao",
                                     history_links=ja_postados,
                                     extra_ids=ids_postados)
"""
from __future__ import annotations

import glob
import json
import os
import re

TAG = "renatoteodoro"
MATT = "matt_word=renatoteodoro&matt_tool=94885465"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

SELOS = {"mais vendido", "black friday", "oferta do dia", "oferta relampago",
         "recomendado", "novo", "full", "cheapest", "ir para produto"}

JS_CARDS = r"""
() => {
  const out = [];
  document.querySelectorAll('a[href*="/p/MLB"]').forEach(a => {
    const mm = (a.href || '').match(/\/p\/(MLB\d{6,})/);
    if (!mm) return;
    let card = a;
    for (let i = 0; i < 8 && card; i++) {
      const t = card.innerText || '';
      if (t.match(/R\$\s*[\d.]/) && t.length > 30) break;
      card = card.parentElement;
    }
    if (!card) return;
    const txt = (card.innerText || '').trim();
    if (!txt) return;
    out.push({ catalog_id: mm[1], href: a.href.split('?')[0], txt: txt.slice(0, 500) });
  });
  return out;
}
"""

JS_IMGS = r"""
() => {
  const mapa = {};
  document.querySelectorAll('img').forEach(img => {
    const src = img.currentSrc || img.src || img.getAttribute('data-src') || '';
    if (!src || src.indexOf('mlstatic') === -1) return;
    if (src.indexOf('D_Q_NP') === -1 && src.indexOf('D_NQ_NP') === -1) return;
    let el = img;
    for (let i = 0; i < 12 && el; i++) {
      const a = el.querySelector ? el.querySelector('a[href*="/p/MLB"]') : null;
      if (a) {
        const m = (a.href || '').match(/\/p\/(MLB\d{6,})/);
        if (m && !mapa[m[1]]) { mapa[m[1]] = src; return; }
      }
      el = el.parentElement;
    }
  });
  return mapa;
}
"""


def _num(trecho):
    try:
        return float(trecho.replace(".", "").replace(",", "."))
    except (ValueError, AttributeError):
        return None


def _slug(texto):
    """Assinatura grosseira do produto para comparar titulos."""
    import unicodedata
    t = unicodedata.normalize("NFKD", (texto or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return "-".join([p for p in t.split("-") if len(p) > 2][:4])


def parse_card(txt):
    """Le preco no Pix, preco original, desconto, frete e titulo do card."""
    linhas = " ".join(x.strip() for x in txt.split("\n") if x.strip())
    valores = []
    for inteiro, cent in re.findall(r"R\$\s*([\d.]+)\s*(?:,\s*(\d{2}))?", linhas):
        v = _num(inteiro + ("," + cent if cent else ""))
        if v:
            valores.append(v)

    desc = re.search(r"(\d{1,2})\s*%\s*OFF", linhas, re.I)
    preco = original = None
    if len(valores) >= 2:
        preco, original = min(valores[0], valores[1]), max(valores[0], valores[1])
    elif valores:
        preco = valores[0]
    if original and preco and original <= preco:
        original = None

    candidatos = []
    for linha in [x.strip() for x in txt.split("\n") if x.strip()]:
        if len(linha) < 18 or "R$" in linha or "%" in linha:
            continue
        if re.fullmatch(r"[\d.,\s]+", linha):
            continue
        if re.search(r"frete|vendidos|classifica|outros meios|\bpix\b", linha, re.I):
            continue
        if linha.strip().lower() in SELOS:
            continue
        candidatos.append(linha)

    return {
        "preco": preco,
        "preco_original": original,
        "desconto": int(desc.group(1)) if desc else None,
        "frete_gratis": bool(re.search(r"frete\s*gr[áa]tis", linhas, re.I)),
        "titulo": max(candidatos, key=len) if candidatos else "",
    }


def entradas_meli_la(divulgacao_dir, limite=8):
    """Colhe links meli.la dos roteiros anteriores (a vitrine precisa deles)."""
    vistos = []
    arquivos = sorted(glob.glob(os.path.join(divulgacao_dir, "roteiro_*.json")), reverse=True)
    for arq in arquivos:
        if len(vistos) >= limite * 12:
            break
        try:
            dados = json.load(open(arq, encoding="utf-8"))
        except Exception:
            continue
        for link in dados.get("links") or []:
            if link and "meli.la" in link and link not in vistos:
                vistos.append(link)
    return vistos[:limite]


def buscar_ofertas_vitrine(divulgacao_dir, history_links=None, extra_ids=None,
                           cooldown_days=30, limite_entradas=8, min_desconto=10,
                           preco_min=20.0, preco_max=7000.0, verbose=True):
    """Devolve ofertas no mesmo formato do coletor oficial, com preco ao vivo."""
    from playwright.sync_api import sync_playwright

    entradas = entradas_meli_la(divulgacao_dir, limite=limite_entradas)
    if not entradas:
        if verbose:
            print("  🛰️ Vitrine: nenhum link meli.la nos roteiros anteriores; sem ponto de entrada.")
        return []

    bloqueados = {str(x).upper() for x in (extra_ids or ())}
    bloqueados |= {str(x) for x in (history_links or ())}
    bloqueados_slug = {_slug(x) for x in (history_links or ())}

    coletados = {}
    with sync_playwright() as pw:
        nav = pw.chromium.launch(headless=True, args=[
            "--no-sandbox", "--disable-dev-shm-usage", "--js-flags=--max-old-space-size=256"])
        pg = nav.new_page(user_agent=USER_AGENT, locale="pt-BR",
                          viewport={"width": 1440, "height": 1000})
        try:
            for i, entrada in enumerate(entradas, 1):
                try:
                    pg.goto(entrada, timeout=60000, wait_until="domcontentloaded")
                    pg.wait_for_timeout(4500)
                    for _ in range(7):
                        pg.mouse.wheel(0, 3200)
                        pg.wait_for_timeout(850)
                    cards = pg.evaluate(JS_CARDS)
                    imgs = pg.evaluate(JS_IMGS)
                except Exception as exc:
                    if verbose:
                        print(f"  🛰️ Vitrine entrada {i}: {type(exc).__name__} {str(exc)[:60]}")
                    continue

                novos = 0
                for card in cards:
                    cid = card["catalog_id"]
                    if cid in coletados:
                        continue
                    dados = parse_card(card["txt"])
                    if not dados["preco"] or not dados["titulo"]:
                        continue
                    imagem = imgs.get(cid, "")
                    if not imagem:
                        continue
                    if not dados["preco_original"] or (dados["desconto"] or 0) < min_desconto:
                        continue
                    if not (preco_min <= dados["preco"] <= preco_max):
                        continue
                    if cid in bloqueados or _slug(dados["titulo"]) in bloqueados_slug:
                        continue
                    dados.update({
                        "item_id": cid,
                        "catalog_id": cid,
                        "product_id": cid,
                        "href": card["href"],
                        "imagem": imagem,
                        "imagens": [imagem],
                        "link": f"{card['href']}?{MATT}",
                        "fonte": "vitrine_afiliado",
                        "categoria": "vitrine",
                    })
                    coletados[cid] = dados
                    novos += 1
                if verbose:
                    print(f"  🛰️ Vitrine entrada {i}: {len(cards)} cards, +{novos} novas, "
                          f"total {len(coletados)}")
        finally:
            nav.close()

    if verbose:
        print(f"  🛰️ Vitrine: {len(coletados)} ofertas com preço ao vivo "
              f"(cooldown de {cooldown_days} dias aplicado)")
    return list(coletados.values())
