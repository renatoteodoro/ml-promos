#!/usr/bin/env python3
"""
Métrica de seleção de ofertas do Promo das Galáxias (definida 08/08/2026,
revisada 12/08/2026 com análise de conversão — distribuição 30/20/15/15/10/8/2):

Prioridade de preço (baseada em densidade do catálogo + desconto + comissão):
- MICRO:   R$ 20-50    → 2%  dos posts (catálogo escasso, comissão baixa)
- CORE:    R$ 50-100   → 10% dos posts (impulso barato, entrada de funil)
- CORE+:   R$ 100-200  → 20% dos posts (melhor desconto médio do catálogo)
- MÉDIO:   R$ 200-500  → 30% dos posts (maior potencial: densidade x desconto)
- OPORT.:  R$ 500-1000 → 15% dos posts (ticket médio-alto)
- ALTO:    R$ 1000-3000→ 15% dos posts (comissão forte, bom volume de catálogo)
- PREMIUM: R$ 3000-7000→ 8%  dos posts (ticket alto, menor volume)
- EVITAR:  acima de R$ 7000

Anti-repetição:
- Histórico em ~/divulgacao/historico_ofertas.json (links já postados)
- Nunca repetir produto já postado em dias anteriores
- Nunca repetir o mesmo link dentro do mesmo dia
"""
import os, json, datetime

HISTORICO_PATH = os.path.expanduser("~/divulgacao/historico_ofertas.json")

def carregar_historico():
    """Carrega o histórico de links já postados."""
    if os.path.exists(HISTORICO_PATH):
        with open(HISTORICO_PATH) as f:
            return json.load(f)
    return {"links": {}, "dias": {}}

def salvar_historico(hist):
    with open(HISTORICO_PATH, "w") as f:
        json.dump(hist, f, ensure_ascii=False, indent=1)

def registrar_posts(links_postados, data=None):
    """Registra links postados no histórico (para não repetir amanhã)."""
    data = data or datetime.date.today().isoformat()
    hist = carregar_historico()
    for link in links_postados:
        if link:
            hist["links"][link] = data
    hist["dias"][data] = hist.get("dias", {}).get(data, 0) + len(links_postados)
    salvar_historico(hist)
    return len(links_postados)

def _familia(o):
    """Chave de família de produto: título normalizado cortado APÓS a 1ª unidade de medida.

    SEM preço na chave: 2 anúncios do MESMO produto (mesmo título, vendedores/preços
    diferentes) colapsam — o distribuidor postava 13 produtos 2x no roteiro (11/08).
    Cortar APÓS a unidade (incluindo-a) evita colapsar tamanhos diferentes
    (Mochila 40l ≠ Mochila 60l; Fone 5.3 com mic ≠ sem mic — sem unidade, título inteiro).
    Unidades precedidas de dígito evitam cortar palavras como "galaxy".
    """
    import re, unicodedata
    t = unicodedata.normalize("NFD", o.get("titulo", "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9]", "", t)
    m = re.search(r"\d+(?:kg|g|mg|ml|l|un|cm|mm|pol|gb|tb|mah|w|hz)", t)
    if m:
        t = t[: m.end()]
    return t


def filtrar_por_metrica(ofertas, n_desejado=98, ja_postados=None):
    """
    Filtra e prioriza ofertas pela métrica de preço.
    - Remove já postados (histórico)
    - Considera somente produtos até R$ 7000
    - Prioriza: 60% core, 20% médio, 10% oportunidade e 10% alto ticket
    """
    ja_postados = ja_postados or set()
    # Remover já postados e produtos acima de R$ 7000
    candidatas = []
    for o in ofertas:
        link = o.get("link", "")
        if link in ja_postados:
            continue
        p = o["preco"]
        desc = o.get("desconto") or 0
        if p > 7000:
            continue
        candidatas.append(o)

    # Deduplicar por família de produto (mesmo produto/variantes com mesmo preço)
    # Ex: 2 sabores de Hipercalórico Dark Mass 3kg a R$119,90 entravam juntos no roteiro.
    vistos, dedup = {}, []
    for o in candidatas:
        chave = _familia(o)
        if chave in vistos:
            idx = vistos[chave]
            if (o.get("desconto") or 0) > (dedup[idx].get("desconto") or 0):
                dedup[idx] = o
            continue
        vistos[chave] = len(dedup)
        dedup.append(o)
    candidatas = dedup

    # Classificar por faixa (7 faixas — revisão de conversão 12/08)
    f_micro = [o for o in candidatas if 20 <= o["preco"] <= 50]
    f_core = [o for o in candidatas if 50 < o["preco"] <= 100]
    f_corep = [o for o in candidatas if 100 < o["preco"] <= 200]
    f_medio = [o for o in candidatas if 200 < o["preco"] <= 500]
    f_oport = [o for o in candidatas if 500 < o["preco"] <= 1000]
    f_alto = [o for o in candidatas if 1000 < o["preco"] <= 3000]
    f_premium = [o for o in candidatas if 3000 < o["preco"] <= 7000]

    # Ordenar cada faixa por desconto (maior primeiro)
    for faixa in (f_micro, f_core, f_corep, f_medio, f_oport, f_alto, f_premium):
        faixa.sort(key=lambda o: o.get("desconto") or 0, reverse=True)

    # Montar proporção 30/20/15/15/10/8/2 (soma = 100%)
    n_medio = int(n_desejado * 0.30)
    n_corep = int(n_desejado * 0.20)
    n_oport = int(n_desejado * 0.15)
    n_alto = int(n_desejado * 0.15)
    n_core = int(n_desejado * 0.10)
    n_premium = int(n_desejado * 0.08)
    n_micro = n_desejado - (n_medio + n_corep + n_oport + n_alto + n_core + n_premium)

    selecionadas = (f_micro[:n_micro] + f_core[:n_core] + f_corep[:n_corep]
                    + f_medio[:n_medio] + f_oport[:n_oport]
                    + f_alto[:n_alto] + f_premium[:n_premium])

    # Se faltar em alguma faixa, completar com a próxima
    faltam = n_desejado - len(selecionadas)
    if faltam > 0:
        resto = [o for o in candidatas if o not in selecionadas]
        resto.sort(key=lambda o: o.get("desconto") or 0, reverse=True)
        selecionadas += resto[:faltam]

    return selecionadas[:n_desejado]

def resumo_metrica(ofertas):
    """Resumo da distribuição para relatório."""
    n = len(ofertas)
    micro = sum(1 for o in ofertas if 20 <= o["preco"] <= 50)
    core = sum(1 for o in ofertas if 50 < o["preco"] <= 100)
    corep = sum(1 for o in ofertas if 100 < o["preco"] <= 200)
    medio = sum(1 for o in ofertas if 200 < o["preco"] <= 500)
    oport = sum(1 for o in ofertas if 500 < o["preco"] <= 1000)
    alto = sum(1 for o in ofertas if 1000 < o["preco"] <= 3000)
    premium = sum(1 for o in ofertas if 3000 < o["preco"] <= 7000)
    acima_limite = sum(1 for o in ofertas if o["preco"] > 7000)
    return {
        "total": n,
        "micro_20_50": micro,
        "core_50_100": core,
        "corep_100_200": corep,
        "medio_200_500": medio,
        "oportunidade_500_1000": oport,
        "alto_1000_3000": alto,
        "premium_3000_7000": premium,
        "acima_7000": acima_limite,
        "preco_medio": round(sum(o["preco"] for o in ofertas) / n) if n else 0,
    }

if __name__ == "__main__":
    # Teste rápido
    hist = carregar_historico()
    print(f"Histórico: {len(hist['links'])} links únicos já postados")
