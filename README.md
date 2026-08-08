# 🛒 ML Promos — Buscador automático de promoções do Mercado Livre

Script que busca promoções no Mercado Livre, injeta **seu link de afiliado** e envia as ofertas para o **JARVIS** (assistente) aprovar e postar no grupo do WhatsApp.

## 🎯 Como funciona (sem API, sem token!)

O script extrai as ofertas da **página de ofertas do site** (https://www.mercadolivre.com.br/ofertas) — funciona em qualquer rede (inclusive VPS), sem precisar de token OAuth nem de app no Developers.

```
ml-promos/
├── ml_promo.py              ← o script principal (busca + link + envio)
├── ml_card.py               ← gera o card de anúncio (foto + preço + link)
├── install.bat              ← instalador Windows (clique 2x)
├── ml_promo.bat             ← usado pelo Agendador do Windows
└── README.md                ← este arquivo
```

## 🚀 Instalação no Windows 11 (Dell G15)

### Pré-requisito
- **Python 3** instalado de https://www.python.org/downloads/
- Na instalação, **MARQUE** a opção **"Add Python to PATH"** (importante!)

### Passos

**1. Baixe/extraia esta pasta** para `C:\ml-promos\` (ou onde preferir).

**2. Edite sua tag de afiliado** (se necessário):
- Abra `ml_promo.py` com o Bloco de Notas
- A linha `AFF_TAG = "matt:renatoteodoro:94885465"` já vem preenchida
- Se trocar de conta, atualize pelo painel https://afiliados.mercadolivre.com.br

**3. Rode o instalador:**
- Dê **2 cliques** em `install.bat`
- Ele testa o script e agenda a tarefa (10h e 20h) no Agendador do Windows

**4. Teste manual (opcional):**
```
python ml_promo.py --ofertas-do-dia
```

## ⏰ Como funciona o fluxo

```
10h/20h → script busca ofertas → envia ao JARVIS (webhook)
       → JARVIS formata e manda no WhatsApp → você aprova
       → JARVIS posta no grupo "Promo das Galáxias"
```

## 🔧 Comandos úteis

```bash
# Ofertas do dia (funciona sempre)
python ml_promo.py --ofertas-do-dia

# Filtrar por desconto mínimo
python ml_promo.py --ofertas-do-dia --desconto 20

# Só frete grátis
python ml_promo.py --ofertas-do-dia --frete-gratis

# Gerar card de anúncio (foto + preço + cupom + link)
python ml_card.py --titulo "Produto X" --preco 118 --preco-original 249 \
  --foto URL --link "https://meli.la/xxx" --chamada "OFERTA!" --cupom "PROMO15"
```

## ❓ Problemas comuns

| Problema | Solução |
|---|---|
| `Python não encontrado` | Instale Python e marque "Add to PATH" |
| `Nenhuma oferta encontrada` | O ML pode ter mudado o layout — rode de novo mais tarde |
| `HTTP Error 404` na busca | Use `--ofertas-do-dia` (busca por palavra cai no anti-bot) |

## 🛡️ Segurança

- O script envia apenas título, preço e link (com sua tag) — sem dados pessoais
- O webhook usa assinatura HMAC V2 (o script calcula sozinho)
- A tag de afiliado é sua identidade de comissão — não compartilhe
