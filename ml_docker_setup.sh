#!/bin/bash
# Roda o Chromium headed (com display Xvfb) dentro de container Docker
# para tentar resolver o reCAPTCHA do login ML.
set -e

# Baixar imagem com Xvfb + chromium
echo "=== Baixando imagem com Xvfb + Chromium ==="
docker pull dorowu/ubuntu-desktop-lxde-vnc:latest 2>&1 | tail -2 || true

# Alternativa mais leve: usar imagem python + xvfb
docker pull python:3.11-slim 2>&1 | tail -1

echo "=== Imagens prontas ==="
docker images | grep -E "python|ubuntu-desktop" | head -3
