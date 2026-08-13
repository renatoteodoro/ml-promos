#!/usr/bin/env python3
"""
Roteiro diário "Promo das Galáxias" — 100 postagens com horários exatos.

Gera o roteiro completo do dia:
- Post 1 (08:00): Abertura "Bom dia" (rotaciona variantes)
- Posts 2-99: Ofertas reais do dia (98 produtos diferentes, cada um com card)
- Post 100 (21:54): Encerramento "Boa noite" (rotaciona variantes)

Horários fixos conforme cronograma do Renato (25 ciclos, intervalos 10→31min).
"""
import json, os, sys, time, hashlib

# ── Cronograma de teste: 140 ofertas, 08:00→23:00 ─────────────────────
# 35 ciclos de 4 ofertas: 5 min entre ofertas do mesmo ciclo e pausas
# maiores de 10/11 min entre ciclos. Abertura e encerramento incluídos.
def _gerar_horarios(n_ofertas=140):
    from datetime import datetime, timedelta
    inicio = datetime.strptime("08:00", "%H:%M")
    fim = datetime.strptime("23:00", "%H:%M")
    ciclo = 4
    ciclos = (n_ofertas + ciclo - 1) // ciclo
    horarios = [inicio]
    atual = inicio
    enviados = 0
    for c in range(ciclos):
        quantidade = min(ciclo, n_ofertas - enviados)
        for j in range(quantidade):
            atual += timedelta(minutes=5)
            horarios.append(atual)
        enviados += quantidade
        if enviados < n_ofertas:
            # Com 140 ofertas e 5 min entre cada uma, restam 195 min
            # para as 34 pausas de ciclo: 25 pausas de 6 min + 9 de 5 min.
            # Pausas de 10-12 min não cabem mantendo 08:00-23:00.
            pausa = 6 if c < 25 else 5
            atual += timedelta(minutes=pausa)
    # Cinco minutos entre a última oferta e o encerramento.
    horarios.append(fim)
    return [h.strftime("%H:%M") for h in horarios]

HORARIOS = _gerar_horarios(140)

# ── Aberturas (Post 1) — sempre diferentes ──────────────────────────────
ABERTURAS = [
    "☀️ BOM DIA, GALÁXIA! 🌌\n\nO dia começou e as ofertas TAMBÉM! 🚀\nAbrimos oficialmente a sessão de promoções de hoje — prepare o carrinho, porque está IMPERDÍVEL! 🔥",
    "🌅 Bom dia, turma! ☀️\n\nÉ com muito prazer que declaro: AS OFERTAS DO DIA ESTÃO NO AR! 🛒✨\nBora garantir as melhores chances antes que esgotem? 🚀",
    "☀️☀️ BOM DIA! ☀️☀️\n\nBem-vindos de volta à Galáxia das promoções! 🪐\nHoje tem MUITA coisa boa chegando — fica de olho, porque a primeira já vem forte! 🔥🚀",
    "🌄 BOM DIA, GUERREIROS DAS OFERTAS! 💪\n\nNovo dia, novas chances de economizar! 💰\nAs promoções de hoje acabaram de abrir — bora conferir? 🛒✨",
    "☀️ Bom dia, Galáxia! 🌌\n\nO café passou e as OFERTAS NÃO DORMEM! ☕🔥\nDeclaro oficialmente ABERTA a temporada de descontos de hoje! 🚀🛒",
    "🌈 BOM DIA, PROMOZEIROS! 🚀\n\nSe preparem... porque hoje o grupo vai bombar! 💣🔥\nAs ofertas do dia estão oficialmente liberadas — quem chega primeiro, garante! 🛒⚡",
    "☀️☀️ BOM DIA, FAMÍLIA! ☀️☀️\n\nHoje é dia de CAÇA ÀS OFERTAS! 🏹💰\nAbriu o expediente de promoções — vem comigo que tem pedrada por aí! 🔥🚀",
]

# ── Encerramentos (Post 100) — sempre diferentes ────────────────────────
ENCERRAMENTOS = [
    "🌙 Boa noite, Galáxia! 🌌\n\nO expediente de ofertas de hoje chegou ao fim! 🙏\nObrigado por acompanhar — amanhã tem MAIS, e a expectativa já está lá em cima! 🚀✨",
    "🌙 BOA NOITE! 🌟\n\nEncerramos as ofertas de hoje com gratidão! 💛\nVocês são o melhor público do universo! Amanhã voltamos com força total! 🚀🌌",
    "🌌 Boa noite, pessoal! 🌙\n\nFim do expediente de hoje — obrigado pela companhia! 🙌\nDescansem que amanhã tem pedrada nova te esperando! 🔥🚀",
    "🌙 BOA NOITE, PROMOZEIROS! 💫\n\nAs ofertas de hoje se encerram por aqui! 🛒\nValeu por cada clique! Amanhã o grupo volta mais quente que nunca! 🔥🌌",
    "🌟 Boa noite, Galáxia! 🌙\n\nExpediente encerrado com chave de ouro! 🗝️✨\nObrigado por fazerem parte — amanhã tem MAIS economia te esperando! 🚀💛",
    "🌙 Boa noite, família! 💤\n\nFechamos as portas das ofertas de hoje! 🚪🛒\nFoi um dia incrível — e amanhã promete ser ainda melhor! Até lá! 🌌✨",
    "🌌🌙 BOA NOITE! 🌙🌌\n\nÚltima chamada do dia: ofertas encerradas! 📢\nMuito obrigado pela participação — amanhã, novos descontos aguardam vocês! 🚀🔥",
]

# ── Chamadas criativas (Posts 2-99) — CURTAS, sem nome do produto ───────
def gerar_chamadas():
    """98 chamadas criativas curtas (sem nome do produto), variadas."""
    padroes = [
        "🔥 IMPERDÍVEL! CORRE QUE É HOJE!",
        "💰 ECONOMIA DE VERDADE!",
        "⚡ CORRE, QUE ISSO ACABA!",
        "✨ A OFERTA QUE VOCÊ ESPERAVA!",
        "🚀 OPORTUNIDADE ÚNICA!",
        "🎯 PRA QUEM TAVA ESPERANDO!",
        "💥 BOMBA! DESCONTO ABSURDO!",
        "🛒 QUALIDADE QUE CABE NO BOLSO!",
        "🌟 DESTAQUE DO DIA!",
        "🔥 NÃO DÁ PRA DEIXAR PASSAR!",
        "🎁 PRESENTE QUE ECONOMIZA!",
        "⚡ PROMO RELÂMPAGO!",
        "💰 SEU BOLSO AGRADECE!",
        "✨ OPORTUNIDADE DE OURO!",
        "🚀 PRA FACILITAR SUA VIDA!",
        "🎯 PRA QUEM É ESPERTO!",
        "🔥 TÁ CARO? NÃO MAIS!",
        "💥 O QUERIDINHO DO GRUPO!",
        "🛒 SÓ HOJE, IMPERDÍVEL!",
        "🌟 POR QUE PAGAR MAIS?",
        "⚡ CORRE QUE ACABA!",
        "💰 ECONOMIZOU AQUI!",
        "✨ PREÇO JUSTO, FINALMENTE!",
        "🚀 QUEM VIU, APROVEITOU!",
        "🎯 DESCONTO IMPERDÍVEL!",
        "🔥 OFERTA DE RESPEITO!",
        "💥 TUDO O QUE VOCÊ PRECISA!",
        "🛒 APROVEITE ANTES QUE VOLTE!",
        "🌟 O GRUPO TÁ PEGANDO FOGO!",
        "⚡ ATENÇÃO, OFERTA RELÂMPAGO!",
        "💰 ECONOMIA QUE VOCÊ SENTE!",
        "✨ PARECE ATÉ PRESENTE!",
        "🚀 SEU MOMENTO DE COMPRAR!",
        "🎯 O PREÇO CERTO, NA HORA CERTA!",
        "🔥 OPORTUNIDADE DE HOJE!",
        "💥 ACABOU O ESTOQUE? CORRE!",
        "🛒 PROMOÇÃO PRA VALER!",
        "🌟 SEU NOVO FAVORITO!",
        "⚡ CORRA ENQUANTO TEM!",
        "💰 A OFERTA QUE MERECE DESTAQUE!",
        "✨ COMPRAR AGORA É A DECISÃO CERTA!",
        "🚀 PROMOÇÃO DE OUTRO MUNDO!",
        "🎯 ACERTE EM CHEIO!",
        "🔥 QUEM ESPEROU, ECONOMIZOU!",
        "💥 O MELHOR PREÇO TÁ AQUI!",
        "🛒 IMPERDÍVEL, INACREDITÁVEL!",
        "🌟 A PEDIDA DO DIA!",
        "⚡ NINGUÉM DEIXA PASSAR!",
        "💰 TODO MUNDO MERECE ECONOMIZAR!",
        "✨ QUALIDADE TOP, PREÇO TOP!",
        "🚀 LANÇAMENTO DE OFERTA!",
        "🎯 PRA QUEM SABE APROVEITAR!",
        "🔥 QUEIMA DE ESTOQUE!",
        "💥 NÃO É TODO DIA QUE APARECE!",
        "🛒 VALE CADA CENTAVO!",
        "🌟 DESTAQUE ABSOLUTO!",
        "⚡ OFERTA LIMITADA!",
        "💰 SUA CARTEIRA VAI AGRADECER!",
        "✨ OFERTA NOTA 10!",
        "🚀 O DESTAQUE DA GALÁXIA!",
        "🎯 NA MIRA DO DESCONTO!",
        "🔥 QUENTINHO, ACABOU DE SAIR!",
        "💥 PREÇO QUE PARECE ERRO!",
        "🛒 CARRINHO ESPERANDO!",
        "🌟 SÓ VANTAGENS!",
        "⚡ SEM TEMPO A PERDER!",
        "💰 ECONOMIZAR NUNCA FOI TÃO FÁCIL!",
        "✨ O DESCONTO QUE MUDA TUDO!",
        "🚀 OFERTA EM ÓRBITA!",
        "🎯 PRECISÃO CIRÚRGICA NO BOLSO!",
        "🔥 MAIS UM ACHADO DE HOJE!",
        "💥 COM ESSE DESCONTO, É QUASE DE GRAÇA!",
        "🛒 COMPRE AGORA OU SE ARREPENDA!",
        "🌟 A GALÁXIA INTEIRA RECOMENDA!",
        "⚡ OFERTA DE COMETA: PASSA RÁPIDO!",
        "💰 DINHEIRO ECONOMIZADO É GANHO!",
        "✨ BRILHA MAIS QUE ESTRELA!",
        "🚀 POUSO GARANTIDO NO CARRINHO!",
        "🎯 ALVO CERTEIRO DA ECONOMIA!",
        "🔥 AQUECENDO AS VENDAS!",
        "💥 O IMPACTO VOCÊ SENTE AQUI!",
        "🛒 PROMOÇÃO DE FAZER INVEJA!",
        "🌟 A ESTRELA DAS OFERTAS!",
        "⚡ RAIO DE ECONOMIA NO BOLSO!",
        "💰 O MELHOR INVESTIMENTO DO DIA!",
        "✨ MAGIA DE PREÇO!",
        "🚀 DECOLANDO COM DESCONTO!",
        "🎯 SEM ERRO: É OFERTA E É BOA!",
        "🔥 MAIS UMA QUE NINGUÉM IGNORA!",
        "💥 VOCÊ LEVA, O PREÇO FICA!",
        "🛒 O CARRINHO DO GRUPO APROVA!",
        "🌟 OFERTA COM CARA DE RARIDADE!",
        "⚡ PROMOÇÃO PRA CIMA!",
        "💰 PREÇO BAIXO, FELICIDADE ALTA!",
        "✨ O ACHADO QUE VOCÊ PROCURAVA!",
        "🌌 MAIS UMA ESTRELA DO CÉU DAS OFERTAS!",
        "🪐 ANEL DE DESCONTO SÓ PRA VOCÊ!",
        "🚀 FOGUETE DE ECONOMIA NO BOLSO!",
    ]
    return padroes

def fmt_preco(valor):
    """Formata preço sem centavos quando inteiro (R$ 603 em vez de R$ 603,00)."""
    if valor == int(valor):
        return f"R$ {int(valor):,}".replace(",", ".")
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def resumir_titulo(titulo, max_len=48):
    """Resume o título do produto: corta em hífen/vírgula/parêntese e limita tamanho."""
    t = titulo.strip()
    # Cortar no primeiro separador comum
    for sep in [" - ", " — ", ", ", " (", " [", " | ", "/"]:
        idx = t.find(sep)
        if 0 < idx < max_len:
            t = t[:idx]
            break
    if len(t) > max_len:
        t = t[:max_len].rsplit(" ", 1)[0] + "…"
    return t

def distribuir_ofertas(ofertas, n=140):
    """
    Distribui as ofertas de forma EQUILIBRADA ao longo do dia:
    - Cada ciclo (4 posts) mistura faixas: impulso, médio, oportunidade e alto ticket
    - Nunca mais de 1 oferta cara por ciclo
    - Manhã: mais impulso; tarde/noite: mistura com melhores descontos
    Retorna lista de ofertas na ordem de postagem.
    """
    # Classificar por faixa (7 faixas — revisão de conversão 12/08)
    f_micro = sorted([o for o in ofertas if 20 <= o["preco"] <= 50], key=lambda o: -(o.get("desconto") or 0))
    f_core = sorted([o for o in ofertas if 50 < o["preco"] <= 100], key=lambda o: -(o.get("desconto") or 0))
    f_corep = sorted([o for o in ofertas if 100 < o["preco"] <= 200], key=lambda o: -(o.get("desconto") or 0))
    f_medio = sorted([o for o in ofertas if 200 < o["preco"] <= 500], key=lambda o: -(o.get("desconto") or 0))
    f_oport = sorted([o for o in ofertas if 500 < o["preco"] <= 1000], key=lambda o: -(o.get("desconto") or 0))
    f_alto = sorted([o for o in ofertas if 1000 < o["preco"] <= 3000], key=lambda o: -(o.get("desconto") or 0))
    f_premium = sorted([o for o in ofertas if 3000 < o["preco"] <= 7000], key=lambda o: -(o.get("desconto") or 0))
    faixas = {"micro": f_micro, "core": f_core, "corep": f_corep, "medio": f_medio,
              "oport": f_oport, "alto": f_alto, "premium": f_premium}

    # Fallback: se faltar em alguma faixa, completar com a seguinte
    def pegar_faixa(lista, idx):
        if idx < len(lista):
            return lista[idx]
        return None

    ordem = []
    contadores = {k: 0 for k in faixas}
    ciclos = (n + 3) // 4
    # Agenda de faixas proporcional à métrica 30/20/15/15/10/8/2.
    # Gera a sequência por maior déficit relativo para distribuir ticket alto
    # ao longo do dia, sem concentrá-lo no final.
    metas = {
        "medio": int(n * 0.30),
        "corep": int(n * 0.20),
        "oport": int(n * 0.15),
        "alto": int(n * 0.15),
        "core": int(n * 0.10),
        "premium": int(n * 0.08),
    }
    metas["micro"] = n - sum(metas.values())
    usados = {k: 0 for k in metas}
    agenda_faixas = []
    for pos in range(n):
        disponiveis = [k for k in metas if usados[k] < len(faixas[k])]
        if not disponiveis:
            break
        tipo = max(disponiveis, key=lambda k: (metas[k] - usados[k]) / max(metas[k], 1))
        agenda_faixas.append(tipo)
        usados[tipo] += 1

    # Ordem de fallback entre faixas (quando uma esgota, usa a mais próxima)
    ORDEM_FALLBACK = {
        "micro": ["micro", "core", "corep", "medio", "oport", "alto", "premium"],
        "core": ["core", "corep", "medio", "micro", "oport", "alto", "premium"],
        "corep": ["corep", "medio", "core", "oport", "alto", "micro", "premium"],
        "medio": ["medio", "corep", "oport", "alto", "core", "premium", "micro"],
        "oport": ["oport", "medio", "alto", "corep", "premium", "core", "micro"],
        "alto": ["alto", "oport", "premium", "medio", "corep", "core", "micro"],
        "premium": ["premium", "alto", "oport", "medio", "corep", "core", "micro"],
    }

    for ciclo in range(ciclos):
        padrao = agenda_faixas[ciclo * 4:(ciclo + 1) * 4]

        for tipo in padrao:
            if len(ordem) >= n:
                break
            o = None
            # Tenta a faixa principal, depois as alternativas na ordem
            for tentativa in ORDEM_FALLBACK[tipo]:
                o = pegar_faixa(faixas[tentativa], contadores[tentativa])
                if o:
                    contadores[tentativa] += 1
                    break
            if o is not None:
                ordem.append(o)
            else:
                # Último recurso: qualquer oferta restante — MAS avançar o contador da
                # faixa do item (11/08: sem isso, o item era re-pego depois,
                # duplicando produtos no roteiro).
                resto = [x for x in ofertas if x not in ordem]
                if resto:
                    o = resto[0]
                    for k, lista in faixas.items():
                        if o in lista:
                            contadores[k] = max(contadores[k], lista.index(o) + 1)
                            break
                    ordem.append(o)
    return ordem[:n]

def construir_roteiro(ofertas, data, dia_idx=0, cards=None, links=None, chamadas=None):
    """Monta o roteiro completo de 142 mensagens: abertura + 140 ofertas + encerramento."""
    chamadas_pool = chamadas if chamadas else gerar_chamadas()
    posts = []

    # Post 1 — Abertura
    abertura = ABERTURAS[dia_idx % len(ABERTURAS)]
    posts.append({"num": 1, "horario": HORARIOS[0], "tipo": "abertura", "texto": abertura, "card": None})

    # Posts 2-141 — 140 ofertas reais, distribuídas de forma equilibrada
    ordem = distribuir_ofertas(ofertas, n=140)
    # MAPA: link original da oferta → índice no array (para casar card/link corretos)
    indice_por_link = {o.get("link", ""): i for i, o in enumerate(ofertas)}
    n_ofertas = len(ordem)
    for i in range(140):
        oferta = ordem[i % n_ofertas]
        # Índice ORIGINAL da oferta (a distribuição reordena! card/link/chamada precisam do índice original)
        idx_orig = indice_por_link.get(oferta.get("link", ""), i % len(ofertas))
        chamada = chamadas_pool[idx_orig % len(chamadas_pool)] if chamadas_pool else "🔥 OFERTA!"
        nome = resumir_titulo(oferta["titulo"])
        # Preços formatados
        preco = fmt_preco(oferta["preco"])
        desc = oferta.get("desconto") or 0
        orig = ""
        economia = ""
        if oferta.get("preco_original") and oferta["preco_original"] > oferta["preco"]:
            orig = f"De {fmt_preco(oferta['preco_original'])} por "
            economia = f"💸 ECONOMIZE {fmt_preco(oferta['preco_original'] - oferta['preco'])}"
            if desc:
                economia += f" (-{desc}%)"
        else:
            # Estimar original a partir do desconto %
            if desc > 0:
                orig_est = round(oferta["preco"] / (1 - desc/100))
                if orig_est > oferta["preco"]:
                    orig = f"De {fmt_preco(orig_est)} por "
                    economia = f"💸 ECONOMIZE {fmt_preco(orig_est - oferta['preco'])} (-{desc}%)"
        # Montar texto no padrão aprovado (chamada e ECONOMIZE em negrito)
        if orig:
            texto = f"*{chamada}*\n\n{nome}\n\n{orig}{preco} no Pix 🛒\n*{economia}*"
        else:
            texto = f"*{chamada}*\n\n{nome}\n\nPor {preco} no Pix 🛒"
        if oferta.get("frete_gratis"):
            if economia:
                texto += " + 🚚 frete grátis"
            else:
                texto += "\n🚚 frete grátis"
        # Cupom ativo (detectado na página do produto)
        cupom = oferta.get("cupom") or {}
        if cupom.get("tem_cupom"):
            desc_cupom = cupom.get("desconto_cupom", "")
            codigo_cupom = cupom.get("codigo_cupom", "")
            if codigo_cupom:
                texto += f"\n🎟️ Cupom: {codigo_cupom}"
                if desc_cupom:
                    texto += f" ({desc_cupom})"
            elif desc_cupom:
                texto += f"\n🎟️ +{desc_cupom} com Cupom"
        # Link: usar meli.la se disponível, senão link completo (pelo índice ORIGINAL)
        link = ""
        if links and idx_orig < len(links) and links[idx_orig]:
            link = links[idx_orig]
        else:
            link = oferta["link"]
        texto += f"\n\n🔗 {link}"
        # Card: usar card[idx_orig] se disponível (foto do produto CORRETO)
        card_path = None
        if cards and idx_orig < len(cards) and cards[idx_orig]:
            card_path = cards[idx_orig]
        posts.append({"num": i+2, "horario": HORARIOS[i+1], "tipo": "oferta", "texto": texto, "card": card_path})

    # Post 142 — Encerramento (23:00)
    encerramento = ENCERRAMENTOS[dia_idx % len(ENCERRAMENTOS)]
    posts.append({"num": 142, "horario": HORARIOS[141], "tipo": "encerramento", "texto": encerramento, "card": None})

    return posts

if __name__ == "__main__":
    print(f"Roteiro: {len(HORARIOS)} horários | {len(ABERTURAS)} aberturas | {len(ENCERRAMENTOS)} encerramentos | {len(gerar_chamadas())} chamadas")
    # Verificar horários
    for i, h in enumerate(HORARIOS):
        if i < len(HORARIOS)-1 and h >= HORARIOS[i+1]:
            print(f"⚠️ Horário fora de ordem: {h} antes de {HORARIOS[i+1]}")
    print(f"✅ {len(HORARIOS)} horários em ordem crescente (08:00 → 22:00)")
