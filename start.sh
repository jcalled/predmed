#!/bin/bash
# PREDMED MVP — Script de inicialização local
set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  🧠  PREDMED MVP — MedOps                    ${NC}"
echo -e "${BLUE}══════════════════════════════════════════════${NC}"
echo ""

# Script de desenvolvimento local: APP_ENV=dev habilita segredo JWT gerado
# localmente, senha de demo e CORS localhost. Fora de dev, defina SECRET_KEY etc.
# (ver backend/.env.example e README).
export APP_ENV="${APP_ENV:-dev}"

# ── Backend ─────────────────────────────────────────────
echo -e "${YELLOW}[1/4] Configurando backend Python...${NC}"
cd backend

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

# Usa o Python do venv diretamente (o activate/shebangs podem apontar para um
# caminho antigo se a pasta do projeto foi movida).
PY="venv/bin/python"
"$PY" -m pip install -r requirements.txt -q

# Copia CSVs se existirem na pasta raiz
if ls ../data/*.csv 1>/dev/null 2>&1; then
  cp ../data/*.csv data/ 2>/dev/null || true
fi

echo -e "${YELLOW}[2/4] Inicializando banco (seed idempotente: só cria o que falta)...${NC}"
"$PY" seed.py

echo -e "${GREEN}[3/4] Iniciando API FastAPI (porta 8000)...${NC}"
"$PY" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

cd ..

# ── Frontend ─────────────────────────────────────────────
echo -e "${YELLOW}[4/4] Configurando frontend Next.js...${NC}"
cd frontend

if [ ! -d "node_modules" ]; then
  npm install --silent
fi

echo -e "${GREEN}Iniciando Next.js (porta 3000)...${NC}"
npm run dev &
FRONTEND_PID=$!

cd ..

echo ""
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅  PREDMED rodando!                        ${NC}"
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo ""
echo "  🌐  Frontend:  http://localhost:3000"
echo "  🔧  Backend:   http://localhost:8000"
echo "  📖  Docs API:  http://localhost:8000/docs"
echo ""
echo "  Ambiente: APP_ENV=${APP_ENV}"
echo "  Usuários de demo (dev): sesa@ / sms@ / hgf@ / particular@predmed.com"
echo "  Senha: definida por SEED_SENHA_PADRAO ou padrão de dev (ver README)"
echo ""
echo "  Para carregar novos CSVs de backend/data/:"
echo "  • cd backend && APP_ENV=dev venv/bin/python seed.py --reimportar"
echo ""
echo "  Pressione Ctrl+C para encerrar"
echo ""

# Aguarda sinal de parada
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'PREDMED encerrado.'" SIGINT SIGTERM
wait
