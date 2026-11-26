#!/usr/bin/env python3
"""Valida se cada link meli.la corresponde à oferta (og:title da página social do portal).

CAUSA RAIZ do incidente 11/08: ml_gerar_links_lotes.py extrai meli.la do DOM inteiro da
página do Gerador de Links e assume que os primeiros N correspondem ao lote na ordem.
Resquícios na página (histórico/atraso de render) deslocam a associação — 11 posts (29-39)
foram ao grupo com o link do produto SEGUINTE (+1), ex: Power Bank -> Pipoqueira.

Esta validação resolve o og:title de cada meli.la (a página /social do portal expõe o
produto real via og:title) e substitui por link direto com tag (rastreia igual) os links
que NÃO correspondem à oferta ou não são confirmáveis. Roda na preparação do executor.
"""
import os, sys, json, re, time, unicodedata

sys.path.insert(0, os.path.expanduser("~/ml-promos-repo"))
TAG = "matt_word=renatoteodoro&matt_tool=94885465"

def _norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", s)

def _palavras_chave(titulo):
    stop = {"com", "para", "sem", "preto", "branco", "portatil", "eletrico",
            "universal", "display", "digital", "sabor", "cor", "compre", "mais"}
    return {w for w in _norm(titulo).split() if len(w) >= 4 and w not in stop}

def _bate(titulo, og):
    chaves = _palavras_chave(titulo)
    if not chaves:
        return True
    og_norm = _norm(og)
    acertos = sum(1 for k in chaves if k in og_norm)
    return (acertos / len(chaves)) >= 0.35

def _link_direto(o):
    m = re.search(r"/p/(MLB\d+)", o.get("link", ""))
    if m:
        return f"https://www.mercadolivre.com.br/p/{m.group(1)}?{TAG}"
    return None

def validar_links(json_path, log=print):
    """Valida links meli.la x ofertas via og:title; corrige os não-batentes p/ link direto.

    Retorna (n_links_validados, n_corrigidos, n_sem_confirmacao).
    """
    from ml_executor_diario import carregar_cookies_portal
    from playwright.sync_api import sync_playwright

    with open(json_path) as f:
        dados = json.load(f)
    ofertas = dados.get("ofertas", [])
    links = dados.get("links") or []

    alvos = [(i, o, links[i]) for i, o in enumerate(ofertas)
             if i < len(links) and links[i] and "meli.la" in links[i]]
    if not alvos:
        return (0, 0, 0)

    log(f"🔎 Validando {len(alvos)} links meli.la x ofertas (og:title)...")
    corrigidos, sem_confirmacao = [], []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
        try:
            cookies = carregar_cookies_portal()
            if cookies:
                ctx.add_cookies(cookies)
        except Exception:
            pass
        page = ctx.new_page()
        for i, o, link in alvos:
            og = ""
            try:
                page.goto(link, timeout=20000, wait_until="domcontentloaded")
                time.sleep(1.0)
                try:
                    og = page.locator('meta[property="og:title"]').get_attribute("content", timeout=2500) or ""
                except Exception:
                    og = ""
            except Exception:
                og = ""
            if not og:
                sem_confirmacao.append(i + 1)
                novo = _link_direto(o)
                if novo:
                    links[i] = novo
                    corrigidos.append((i + 1, "sem og:title"))
                continue
            if not _bate(o.get("titulo", ""), og):
                novo = _link_direto(o)
                if novo:
                    links[i] = novo
                    corrigidos.append((i + 1, og[:50]))
        browser.close()

    dados["links"] = links
    with open(json_path, "w") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)

    n_meli = sum(1 for l in links if l and "meli.la" in l)
    log(f"🔎 Validação: {len(alvos)} meli.la conferidos | corrigidos: {len(corrigidos)} | restam {n_meli} meli.la")
    for num, motivo in corrigidos[:15]:
        log(f"   ↪ Post {num}: link trocado p/ direto com tag ({motivo[:45]})")
    return (len(alvos) - len(corrigidos), len(corrigidos), len(sem_confirmacao))

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/divulgacao/roteiro_2026-08-11.json")
    ok, corr, sem = validar_links(path)
    print(f"\nRESULTADO: {ok} OK | {corr} corrigidos | {sem} sem confirmação")
