#!/usr/bin/env python3
"""
Refresh automático do token OAuth do app Mercado Livre "Promo das Galáxias".
O token expira em 6h (21600s). Este script:
- Verifica se o token está válido ou perto de expirar
- Renova via refresh_token quando necessário
- Pode rodar como cron (ex: a cada 2h) ou ser chamado antes do uso

Uso:
  python3 ml_refresh_token.py          # renova se expirou/expira em < 1h
  python3 ml_refresh_token.py --force  # renova sempre
  python3 ml_refresh_token.py --check  # só verifica e mostra status
"""
import os, sys, json, time, argparse, urllib.request, urllib.parse, datetime

TOKEN_PATH = os.path.expanduser("~/.hermes/mcp-tokens/mercadolibre_app.token.json")
CLIENT_ID = "7193684766645948"
CLIENT_SECRET = "iyn0lDkUkLqL9tbo47ToeP4EjhXHYF21"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
# Renovar quando faltar menos que isso para expirar
MARGIN = 3600  # 1h

def carregar():
    with open(TOKEN_PATH) as f:
        return json.load(f)

def salvar(tok):
    with open(TOKEN_PATH, "w") as f:
        json.dump(tok, f, indent=1)

def tempo_restante(tok):
    """Segundos até expirar, baseado no campo expires_at (timestamp real)."""
    exp = tok.get("expires_at") or tok.get("created_at", 0) + tok.get("expires_in", 21600)
    return exp - time.time()

def renovar():
    tok = carregar()
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": tok["refresh_token"],
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            novo = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"❌ Refresh falhou: {e.code} {e.read().decode()[:200]}")
        return False

    # Salvar com timestamp real de expiração
    agora = time.time()
    novo["expires_at"] = agora + novo.get("expires_in", 21600)
    novo["refreshed_at"] = agora
    novo["user_id"] = tok.get("user_id")
    salvar(novo)
    print(f"✅ Token renovado! Expira em {novo['expires_in']/3600:.1f}h (às {datetime.datetime.fromtimestamp(novo['expires_at']).strftime('%H:%M')})")
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="Renova sempre")
    ap.add_argument("--check", action="store_true", help="Só verifica")
    args = ap.parse_args()

    if not os.path.exists(TOKEN_PATH):
        print(f"❌ Token não encontrado em {TOKEN_PATH}")
        sys.exit(1)

    tok = carregar()
    restante = tempo_restante(tok)
    horas = restante / 3600
    status = "válido" if restante > 0 else "EXPIRADO"
    print(f"📊 Token {status}: {horas:.1f}h restantes ({datetime.datetime.fromtimestamp(time.time() + restante).strftime('%H:%M')} se válido)")

    if args.check:
        sys.exit(0 if restante > 0 else 1)

    if restante < MARGIN or args.force:
        ok = renovar()
        sys.exit(0 if ok else 1)
    else:
        print("⏳ Token ainda válido, sem refresh necessário.")
        sys.exit(0)

if __name__ == "__main__":
    main()
