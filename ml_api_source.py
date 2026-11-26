#!/usr/bin/env python3
"""Fonte de contingência de ofertas usando a API oficial do Mercado Livre.

O endpoint público /ofertas pode devolver a página de verificação da VPS sem
lançar erro HTTP. Este módulo usa highlights apenas para descobrir produtos;
preço, desconto, imagem e vendedor vêm dos endpoints oficiais de catálogo.
Só aceita o menor anúncio novo do catálogo quando ele próprio informa
original_price > price. Não tenta contornar bloqueios do site.
"""

import datetime
import glob
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from email.utils import parsedate_to_datetime

from ml_metrica import HISTORICO_PATH, REPETICAO_COOLDOWN_DIAS

API = "https://api.mercadolibre.com"
USER_AGENT = "PromoGalaxias/1.0 (ofertas via API oficial)"
REQUEST_DELAY = 1.2
REQUEST_JITTER = 0.25
MIN_PRICE = 20.0
MAX_PRICE = 7000.0

# Categorias amplas mais algumas folhas com itens de maior ticket. Highlights
# pode retornar ITEM/USER_PRODUCT; só PRODUCT tem catálogo e mídia públicos.
CATEGORIAS = [
    ("MLB1055", "Celulares e smartphones"),
    ("MLB1002", "Televisores"),
    ("MLB430687", "Portáteis e acessórios de informática"),
    ("MLB1576", "Refrigeração"),
    ("MLB438282", "Lavadores"),
    ("MLB1580", "Fornos e fogões"),
    ("MLB252358", "Ar e ventilação"),
    ("MLB2830", "Projetores e telas"),
    ("MLB1712", "Componentes para PC"),
    ("MLB447778", "PC gaming"),
    ("MLB3835", "Áudio"),
    ("MLB436380", "Móveis para casa"),
    ("MLB438284", "Pequenos eletrodomésticos"),
    ("MLB1338", "Fitness e musculação"),
    ("MLB2526", "Ferramentas elétricas"),
    ("MLB3813", "Acessórios para celulares"),
    ("MLB417704", "Smartwatches"),
    ("MLB6284", "Perfumes"),
    ("MLB199407", "Cuidados com a pele"),
    ("MLB1618", "Cozinha"),
    ("MLB430598", "Armazenamento de informática"),
    ("MLB5672", "Acessórios para veículos"),
    ("MLB271599", "Agro"),
    ("MLB1403", "Alimentos e bebidas"),
    ("MLB1071", "Animais"),
    ("MLB1367", "Antiguidades e coleções"),
    ("MLB1368", "Arte, papelaria e armarinho"),
    ("MLB1384", "Bebês"),
    ("MLB1246", "Beleza e cuidado pessoal"),
    ("MLB1132", "Brinquedos e hobbies"),
    ("MLB1430", "Calçados, roupas e bolsas"),
    ("MLB1039", "Câmeras e acessórios"),
    ("MLB1574", "Casa, móveis e decoração"),
    ("MLB1051", "Celulares e telefones"),
    ("MLB1500", "Construção"),
    ("MLB5726", "Eletrodomésticos"),
    ("MLB1000", "Eletrônicos, áudio e vídeo"),
    ("MLB1276", "Esportes e fitness"),
    ("MLB263532", "Ferramentas"),
    ("MLB12404", "Festas e lembrancinhas"),
    ("MLB1144", "Games"),
    ("MLB1499", "Indústria e comércio"),
    ("MLB1648", "Informática"),
    ("MLB1182", "Instrumentos musicais"),
    ("MLB3937", "Joias e relógios"),
    ("MLB1196", "Livros, revistas e comics"),
    ("MLB1168", "Música, filmes e seriados"),
    ("MLB264586", "Saúde"),
    ("MLB1953", "Mais categorias"),
]

# Busca pública oficial por termos para ampliar a descoberta quando highlights
# não trazem 140 ofertas novas com desconto. Os preços continuam sendo validados
# exclusivamente no catálogo /products/{id}/items.
# Termos sazonais priorizados no período de Natal. A busca continua usando
# catálogo e preço atual da API oficial, sem reaproveitar preço antigo.
PESQUISAS_NATALINAS = [
    ("enfeites de natal", "Natal e decoração"),
    ("árvore de natal", "Natal e decoração"),
    ("luzes de natal", "Natal e decoração"),
    ("pisca pisca natal", "Natal e decoração"),
    ("guirlanda de natal", "Natal e decoração"),
    ("presépio", "Natal e decoração"),
]

PESQUISAS = [
    ("smartphone", "Celulares e smartphones"),
    ("notebook", "Informática"),
    ("fone bluetooth", "Áudio"),
    ("air fryer", "Cozinha"),
    ("smart tv", "Televisores"),
    ("monitor gamer", "Informática"),
    ("cadeira gamer", "Móveis e informática"),
    ("tablet", "Informática"),
    ("smartwatch", "Smartwatches"),
    ("cafeteira", "Cozinha"),
    ("liquidificador", "Cozinha"),
    ("aspirador de pó", "Eletrodomésticos"),
    ("perfume", "Beleza e cuidado pessoal"),
    ("tênis feminino", "Calçados e roupas"),
    ("ferramentas elétricas", "Ferramentas"),
    ("SSD", "Informática"),
    ("ar condicionado inverter", "Ar e ventilação"),
    ("geladeira", "Eletrodomésticos"),
    ("lava e seca", "Eletrodomésticos"),
    ("bicicleta", "Esportes e fitness"),
    ("fralda", "Bebês"),
    ("ração cachorro", "Animais"),
    ("maquiagem", "Beleza e cuidado pessoal"),
    ("ventilador", "Ar e ventilação"),
    ("caixa de som bluetooth", "Áudio"),
    ("barbeador", "Beleza e cuidado pessoal"),
    ("câmera de segurança", "Câmeras e acessórios"),
    ("microfone", "Áudio"),
    ("impressora", "Informática"),
    ("console videogame", "Games"),
]

_ID_RE = re.compile(r"(?<![A-Z0-9])(MLB\d{6,})(?!\d)", re.IGNORECASE)


class MercadoLivreAPIError(RuntimeError):
    """Falha que deve abortar a geração, nunca virar roteiro vazio."""


def catalog_id_from_url(value):
    """Extrai o ID de catálogo do caminho, sem confundir o item_id da query."""
    if not value:
        return ""
    text = str(value).strip()
    if re.fullmatch(r"MLB\d{6,}", text, re.IGNORECASE):
        return text.upper()
    try:
        path = urllib.parse.urlsplit(text).path
    except ValueError:
        path = text.split("?", 1)[0]
    m = re.search(r"/p/(MLB\d{6,})", path, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    m = _ID_RE.search(path)
    return m.group(1).upper() if m else ""


def published_catalog_ids(divulgacao_dir, history_links=(), extra_ids=(),
                          cooldown_days=REPETICAO_COOLDOWN_DIAS, today=None):
    """Lê links recentes e roteiros dentro da janela de repetição para excluir catálogos."""
    today = today or datetime.date.today()
    cooldown_days = max(0, int(cooldown_days))
    ids = {str(x).upper() for x in (extra_ids or ()) if re.fullmatch(r"MLB\d{6,}", str(x), re.IGNORECASE)}
    for value in history_links or ():
        pid = catalog_id_from_url(value)
        if pid:
            ids.add(pid)

    pattern = os.path.join(divulgacao_dir, "roteiro_????-??-??.json")
    for path in glob.glob(pattern):
        mday = re.search(r"roteiro_(\d{4}-\d{2}-\d{2})\.json$", path)
        if not mday:
            continue
        try:
            route_date = datetime.date.fromisoformat(mday.group(1))
        except ValueError:
            continue
        age_days = (today - route_date).days
        if age_days < 0 or age_days >= cooldown_days:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        for offer in data.get("ofertas", []) or []:
            if not isinstance(offer, dict):
                continue
            raw_id = offer.get("catalog_id") or offer.get("product_id")
            pid = catalog_id_from_url(raw_id) or catalog_id_from_url(offer.get("link_original")) or catalog_id_from_url(offer.get("link"))
            if pid:
                ids.add(pid)
        for link in data.get("links", []) or []:
            pid = catalog_id_from_url(link)
            if pid:
                ids.add(pid)
    return ids


def catalog_ids_available_for_reuse(divulgacao_dir, excluded_ids=(),
                                    cooldown_days=REPETICAO_COOLDOWN_DIAS,
                                    today=None, history_path=None):
    """Lista catálogos com último registro >= cooldown; nunca reutiliza preços antigos."""
    today = today or datetime.date.today()
    cooldown_days = max(0, int(cooldown_days))
    history_path = history_path or HISTORICO_PATH
    blocked = {pid for value in (excluded_ids or ())
               if (pid := catalog_id_from_url(value))}
    dates_by_id = {}

    def remember(value, posted_on):
        pid = catalog_id_from_url(value)
        if not pid or pid in blocked:
            return
        age_days = (today - posted_on).days
        if age_days < cooldown_days or age_days < 0:
            return
        if posted_on > dates_by_id.get(pid, datetime.date.min):
            dates_by_id[pid] = posted_on

    for path in glob.glob(os.path.join(divulgacao_dir, "roteiro_????-??-??.json")):
        match = re.search(r"roteiro_(\d{4}-\d{2}-\d{2})\.json$", path)
        if not match:
            continue
        try:
            route_date = datetime.date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if (today - route_date).days < cooldown_days or route_date > today:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        for offer in data.get("ofertas", []) or []:
            if not isinstance(offer, dict):
                continue
            value = (offer.get("catalog_id") or offer.get("product_id")
                     or offer.get("link_original") or offer.get("link"))
            remember(value, route_date)
        for link in data.get("links", []) or []:
            remember(link, route_date)

    try:
        with open(history_path, encoding="utf-8") as f:
            history = json.load(f)
    except (OSError, ValueError):
        history = {}
    for link, raw_date in (history.get("links") or {}).items():
        try:
            posted_on = datetime.date.fromisoformat(str(raw_date)[:10])
        except (TypeError, ValueError):
            continue
        remember(link, posted_on)

    return [pid for pid, _ in sorted(
        dates_by_id.items(), key=lambda item: (item[1], item[0]), reverse=True
    )]


_ACTIVE_TOKEN = None


def _get_token():
    # O helper existente lê o token local e renova quando está perto de expirar.
    global _ACTIVE_TOKEN
    from ml_compare_preco import get_token
    token = get_token()
    if not token:
        raise MercadoLivreAPIError("Token OAuth do Mercado Livre indisponível.")
    _ACTIVE_TOKEN = token
    return token


def _refresh_after_401(previous_token):
    """Recarrega o token rotacionado pelo cron; força refresh só se necessário."""
    global _ACTIVE_TOKEN
    try:
        latest = _get_token()
    except Exception:
        latest = None
    if latest and latest != previous_token:
        _ACTIVE_TOKEN = latest
        return latest

    refresh_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml_refresh_token.py")
    try:
        result = subprocess.run(
            [sys.executable, refresh_script, "--force"],
            capture_output=True, text=True, timeout=45,
        )
        if result.returncode != 0:
            return None
        latest = _get_token()
    except Exception:
        return None
    if latest and latest != previous_token:
        _ACTIVE_TOKEN = latest
        return latest
    return None


def _pause_between_requests():
    """Espaça chamadas sequenciais à API e evita rajadas repetitivas."""
    time.sleep(REQUEST_DELAY + random.uniform(0.0, REQUEST_JITTER))


def _retry_after_seconds(headers, attempt):
    """Respeita Retry-After (segundos ou data HTTP); sem header, usa backoff."""
    raw = (headers or {}).get("Retry-After")
    retry_after = None
    if raw:
        try:
            retry_after = max(0.0, float(raw))
        except (TypeError, ValueError):
            try:
                retry_at = parsedate_to_datetime(raw)
                retry_after = max(0.0, retry_at.timestamp() - time.time())
            except (TypeError, ValueError, OverflowError):
                retry_after = None
    fallback = min(2 ** attempt, 120)
    base = max(retry_after or 0.0, fallback)
    return base + random.uniform(0.0, min(5.0, max(0.1, base * 0.1)))


def _get_json(path, token, attempts=6):
    global _ACTIVE_TOKEN
    if _ACTIVE_TOKEN:
        token = _ACTIVE_TOKEN
    token_refreshed = False
    for attempt in range(attempts):
        request = urllib.request.Request(
            API + path,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                return json.load(response), response.status
        except urllib.error.HTTPError as exc:
            code = exc.code
            if code == 401:
                if not token_refreshed and attempt + 1 < attempts:
                    token_refreshed = True
                    replacement = _refresh_after_401(token)
                    if replacement and replacement != token:
                        print("  🔄 API recusou token expirado; token atualizado e consulta repetida.")
                        token = replacement
                        _ACTIVE_TOKEN = replacement
                        continue
                raise MercadoLivreAPIError(
                    "API do Mercado Livre recusou o token OAuth (HTTP 401); "
                    "reload/refresh não recuperou a consulta."
                ) from None
            if code == 429:
                if attempt + 1 < attempts:
                    time.sleep(_retry_after_seconds(exc.headers, attempt))
                    continue
                retry_after = (exc.headers or {}).get("Retry-After", "ausente")
                raise MercadoLivreAPIError(
                    f"Falha na API do Mercado Livre: HTTP 429 em {path.split('?')[0]} "
                    f"após {attempts} tentativas; Retry-After={retry_after}."
                ) from None
            if code in (400, 403, 404):
                return None, code
            if code in (500, 502, 503, 504) and attempt + 1 < attempts:
                time.sleep(min(2 ** attempt, 60) + random.uniform(0.0, 0.5))
                continue
            raise MercadoLivreAPIError(f"Falha na API do Mercado Livre: HTTP {code} em {path.split('?')[0]}.") from None
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            if attempt + 1 < attempts:
                time.sleep(min(2 ** attempt, 60) + random.uniform(0.0, 0.5))
                continue
            raise MercadoLivreAPIError(f"Falha de rede/API do Mercado Livre em {path.split('?')[0]}: {type(exc).__name__}.") from None
    return None, 0


def _eligible_lowest_item(results):
    """Retorna o anúncio novo de menor preço somente se ele tiver desconto real."""
    eligible = []
    for item in results or []:
        if item.get("condition") != "new" or item.get("currency_id") != "BRL":
            continue
        try:
            price = float(item.get("price") or 0)
        except (TypeError, ValueError):
            continue
        if not MIN_PRICE <= price <= MAX_PRICE:
            continue
        eligible.append((price, item))
    if not eligible:
        return None
    price, winner = min(eligible, key=lambda pair: pair[0])
    try:
        original = float(winner.get("original_price") or 0)
    except (TypeError, ValueError):
        return None
    if original <= price:
        return None
    item_id = winner.get("item_id")
    if not item_id:
        return None
    discount = round((original - price) * 100 / original)
    if discount < 1:
        return None
    shipping = winner.get("shipping") or {}
    return {
        "preco": price,
        "preco_original": original,
        "desconto": int(discount),
        "frete_gratis": bool(shipping.get("free_shipping")),
        "item_id": str(item_id),
    }


def buscar_ofertas_highlights(divulgacao_dir, history_links=(), extra_ids=(),
                              limite_ofertas=300,
                              max_produtos=int(os.environ.get("PROMO_MAX_PRODUTOS", "900")),
                              cooldown_days=REPETICAO_COOLDOWN_DIAS,
                              termos_prioritarios=()):
    """Busca ofertas atuais com preço de catálogo, respeitando anti-repetição.

    Highlights e busca oficial só descobrem IDs de catálogo. A oferta só entra
    se o anúncio novo mais barato vier com preço original superior ao atual e
    o produto tiver nome/imagem públicos. Retorna menos do limite se a API não fornecer ofertas.
    """
    token = _get_token()
    ids_ja_publicados = published_catalog_ids(
        divulgacao_dir, history_links, extra_ids, cooldown_days=cooldown_days
    )
    max_produtos = int(max_produtos)
    reusable_ids = catalog_ids_available_for_reuse(
        divulgacao_dir, excluded_ids=ids_ja_publicados,
        cooldown_days=cooldown_days,
    )
    reuse_reserve = min(1200, len(reusable_ids), max_produtos)
    fresh_max_produtos = max_produtos - reuse_reserve
    if reusable_ids:
        print(f"  Histórico: {len(reusable_ids)} catálogos com {cooldown_days}+ dias disponíveis para revalidação; reserva de até {reuse_reserve}/{max_produtos} consultas de preço.")
    produto_ids, categorias_por_id, fontes_por_id = [], {}, {}
    ids_vistos = set()

    # Coloca a temporada na fila antes dos highlights. Assim, quando houver
    # descontos elegíveis, eles entram na mesma coleta e podem ser intercalados
    # no roteiro sem depender da ordem do catálogo geral.
    for termo, category_name in termos_prioritarios or ():
        query = urllib.parse.urlencode({
            "status": "active", "site_id": "MLB", "q": termo,
            "limit": 50, "offset": 0,
        })
        data, status = _get_json(f"/products/search?{query}", token)
        novos_ids = []
        if data:
            for entry in data.get("results") or []:
                pid = catalog_id_from_url(entry.get("id"))
                if not pid or pid in ids_vistos or pid in ids_ja_publicados:
                    continue
                ids_vistos.add(pid)
                categorias_por_id[pid] = category_name
                fontes_por_id[pid] = "ml_api_search_natal"
                produto_ids.append(pid)
                novos_ids.append(pid)
                if len(produto_ids) >= fresh_max_produtos:
                    break
        elif status not in (400, 403, 404):
            print(f"  ⚠️ Busca sazonal '{termo}': HTTP {status}; ignorando a consulta.")
        print(f"  API Natal '{termo}': {len(novos_ids)} produtos novos de catálogo")
        _pause_between_requests()
        if len(produto_ids) >= fresh_max_produtos:
            break

    for category_id, category_name in CATEGORIAS:
        data, status = _get_json(f"/highlights/MLB/category/{category_id}", token)
        if not data:
            if status not in (404, 400):
                print(f"  ⚠️ Highlights {category_id}: HTTP {status}; ignorando a categoria.")
            _pause_between_requests()
            continue
        items = data.get("content") or []
        added = 0
        for entry in items:
            if entry.get("type") != "PRODUCT":
                continue
            pid = catalog_id_from_url(entry.get("id"))
            if not pid or pid in ids_vistos or pid in ids_ja_publicados:
                continue
            ids_vistos.add(pid)
            categorias_por_id[pid] = category_name
            fontes_por_id[pid] = "ml_api_highlights"
            produto_ids.append(pid)
            added += 1
            if len(produto_ids) >= fresh_max_produtos:
                break
        print(f"  API highlights {category_id}: {added} produtos novos de catálogo")
        _pause_between_requests()
        if len(produto_ids) >= fresh_max_produtos:
            break

    candidatos = []
    consultados = 0
    alvo = min(max(int(limite_ofertas), 140), 400)

    def consultar_precos(ids):
        nonlocal consultados
        for pid in ids:
            if len(candidatos) >= alvo:
                break
            payload, status = _get_json(f"/products/{pid}/items?limit=50", token)
            consultados += 1
            if payload and status in (200, 206):
                winner = _eligible_lowest_item(payload.get("results"))
                if winner:
                    winner.update({
                        "catalog_id": pid,
                        "product_id": pid,
                        "fonte": fontes_por_id.get(pid, "ml_api_highlights"),
                        "categoria": categorias_por_id.get(pid, ""),
                        "link": f"https://www.mercadolivre.com.br/p/{pid}?pdp_filters=item_id%3A{urllib.parse.quote(winner['item_id'], safe='')}",
                    })
                    candidatos.append(winner)
            elif status not in (400, 403, 404):
                print(f"  ⚠️ Itens {pid}: HTTP {status}; ignorando o produto.")
            if consultados % 25 == 0:
                print(f"  API preços: {consultados}/{len(produto_ids)} catálogos; {len(candidatos)} ofertas elegíveis")
            _pause_between_requests()

    # Preferir highlights; só ampliar pela busca oficial se a primeira fonte não
    # oferecer o volume pedido. A busca de catálogo aceita offset até 100 (páginas
    # 0/50/100); percorrer em rodadas preserva variedade entre os termos.
    consultar_precos(produto_ids)
    if len(candidatos) < alvo and len(produto_ids) < fresh_max_produtos:
        totais_por_termo = {}
        for offset in (0, 50, 100):
            for termo, category_name in PESQUISAS:
                if len(candidatos) >= alvo or len(produto_ids) >= fresh_max_produtos:
                    break
                total = totais_por_termo.get(termo)
                if total is not None and total <= offset:
                    continue
                query = urllib.parse.urlencode({
                    "status": "active", "site_id": "MLB", "q": termo,
                    "limit": 50, "offset": offset,
                })
                data, status = _get_json(f"/products/search?{query}", token)
                if not data:
                    if offset == 0 or status in (400, 403, 404):
                        totais_por_termo[termo] = 0 if offset == 0 else offset
                    if status not in (400, 403, 404):
                        print(f"  ⚠️ Busca API '{termo}' offset={offset}: HTTP {status}; ignorando a consulta.")
                    _pause_between_requests()
                    continue
                paging = data.get("paging") or {}
                raw_total = paging.get("total")
                try:
                    totais_por_termo[termo] = int(raw_total) if raw_total is not None else None
                except (TypeError, ValueError):
                    totais_por_termo[termo] = None
                novos_ids = []
                for entry in data.get("results") or []:
                    pid = catalog_id_from_url(entry.get("id"))
                    if not pid or pid in ids_vistos or pid in ids_ja_publicados:
                        continue
                    ids_vistos.add(pid)
                    categorias_por_id[pid] = category_name
                    fontes_por_id[pid] = "ml_api_search"
                    produto_ids.append(pid)
                    novos_ids.append(pid)
                    if len(produto_ids) >= fresh_max_produtos:
                        break
                print(f"  API busca '{termo}' offset={offset}: {len(novos_ids)} produtos novos de catálogo")
                consultar_precos(novos_ids)
                _pause_between_requests()
            if len(candidatos) >= alvo or len(produto_ids) >= fresh_max_produtos:
                break

    if len(candidatos) < alvo and reusable_ids:
        remaining = max_produtos - len(produto_ids)
        reuse_batch = [pid for pid in reusable_ids
                       if pid not in ids_vistos and pid not in ids_ja_publicados][:remaining]
        for pid in reuse_batch:
            ids_vistos.add(pid)
            categorias_por_id[pid] = ""
            fontes_por_id[pid] = "ml_api_repeticao_30d"
            produto_ids.append(pid)
        if reuse_batch:
            antes_reuso = len(candidatos)
            print(f"  API repetição: revalidando {len(reuse_batch)} catálogos com 30+ dias para completar a seleção.")
            consultar_precos(reuse_batch)
            print(f"  API repetição: {len(candidatos) - antes_reuso} produtos ainda têm desconto atual válido.")

    ofertas = []
    for index, candidate in enumerate(candidatos, start=1):
        pid = candidate["catalog_id"]
        detail, status = _get_json(f"/products/{pid}", token)
        if detail and status in (200, 206):
            title = (detail.get("name") or "").strip()
            pictures = detail.get("pictures") or []
            image_urls = [p.get("url") or p.get("secure_url") for p in pictures if isinstance(p, dict)]
            image_urls = [u for u in image_urls if u]
            if not image_urls and detail.get("thumbnail"):
                image_urls = [detail["thumbnail"]]
            if title and image_urls and detail.get("status", "active") == "active":
                offer = dict(candidate)
                offer["titulo"] = title
                offer["imagem"] = image_urls[0]
                offer["imagens"] = image_urls[:4]
                ofertas.append(offer)
        elif status not in (400, 403, 404):
            print(f"  ⚠️ Catálogo {pid}: HTTP {status}; ignorando o produto.")
        if index % 25 == 0:
            print(f"  API detalhes: {index}/{len(candidatos)}; {len(ofertas)} ofertas com nome e imagem")
        _pause_between_requests()

    print(f"  API fallback: {len(ids_ja_publicados)} IDs já divulgados excluídos; "
          f"{len(produto_ids)} produtos consultados; {consultados} preços verificados; "
          f"{len(ofertas)} ofertas completas.")
    return ofertas
