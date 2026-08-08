# 🛒 ML Promos — Buscador automático de promoções do Mercado Livre

Script que busca promoções no Mercado Livre, injeta **seu link de afiliado** e envia as ofertas para o **JARVIS** (assistente) aprovar e postar no grupo do WhatsApp.

## ⚠️ IMPORTANTE — ANTES DE COMEÇAR

Este repositório **NÃO contém o token** (arquivo `mcp-tokens/mercadolibre.token.json`) por segurança.
O token é a sua identidade na API do ML — se vazar, alguém pode usar sua conta.

**Você recebe o token por outro canal (WhatsApp/SSH).** Crie a pasta `mcp-tokens/` aqui e coloque o arquivo dentro.

```
ml-promos/
├── ml_promo.py              ← o script principal
├── install.bat              ← instalador Windows (clique 2x)
├── ml_promo.bat             ← usado pelo Agendador do Windows
├── README.md                ← este arquivo
└── mcp-tokens/              ← VOCÊ cria esta pasta (token NÃO está no git)
    └── mercadolibre.token.json
```

## 🚀 Instalação no Windows 11 (Dell G15)

### Pré-requisito
- **Python 3** instalado de https://www.python.org/downloads/
- Na instalação, **MARQUE** a opção **"Add Python to PATH"** (importante!)

### Passos

**1. Baixe/extraia esta pasta** para `C:\ml-promos\` (ou onde preferir).

**2. Coloque o token:**
- Crie a pasta `C:\ml-promos\mcp-tokens\`
- Copie o arquivo `mercadolibre.token.json` para dentro dela
- *(O token você recebe do JARVIS por WhatsApp/SSH — nunca pelo GitHub)*

**3. Edite sua tag de afiliado:**
- Abra `ml_promo.py` com o Bloco de Notas
- Ache a linha `AFF_TAG = "COLE_SUA_TAG_AQUI"`
- Troque pela sua tag real (do painel https://afiliados.mercadolivre.com.br):
  - Link com `matt_word=X&matt_tool=Y` → `AFF_TAG = "matt:X:Y"`
  - Link com `tag=X-20` → `AFF_TAG = "X-20"`

**4. Rode o instalador:**
- Dê **2 cliques** em `install.bat`
- Ele testa o script e agenda a tarefa (10h e 20h) no Agendador do Windows

**5. Teste manual (opcional):**
```
python ml_promo.py --nicho "cama pet" --desconto 15
```

## ⏰ Como funciona o fluxo

```
10h/20h → script busca ofertas → envia ao JARVIS (webhook)
       → JARVIS formata e manda no WhatsApp → você aprova
       → JARVIS posta no grupo "Promo das Galáxias"
```

## 🔧 Comandos úteis

```bash
# Buscar um nicho específico
python ml_promo.py --nicho "tomada inteligente" --desconto 20

# Vários nichos, só frete grátis
python ml_promo.py --nicho "cama pet;ração;brinquedo" --frete-gratis

# Mais resultados por nicho
python ml_promo.py --nicho "arranhador" --limite 10
```

## ❓ Problemas comuns

| Problema | Solução |
|---|---|
| `Python não encontrado` | Instale Python e marque "Add to PATH" |
| `Token não encontrado` | Crie `mcp-tokens\` e copie o token pra dentro |
| `403 — IP bloqueado` | Rode na sua máquina (IP residencial), não em servidor |
| `Erro de rede` | Verifique sua internet / firewall |

## 🛡️ Segurança

- O token NÃO está no repositório (`.gitignore` protege)
- O webhook usa assinatura HMAC (o script calcula sozinho)
- Nunca compartilhe o token ou a pasta `mcp-tokens/`
