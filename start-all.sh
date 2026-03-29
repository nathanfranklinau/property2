#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🛑 Stopping any running services..."

# Kill Next.js dev server (port 3000)
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 1

# Kill Python FastAPI service (port 8001)
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
sleep 1

echo "✅ Services stopped"
echo ""

# Start Python FastAPI service in background
echo "🚀 Starting Python FastAPI service (port 8001)..."
cd "$REPO_DIR/data-layer"
source venv/bin/activate
export ADDRESS_MODEL_DIR="$REPO_DIR/data-layer/training/model"
nohup uvicorn service.main:app --port 8001 --reload > uvicorn.log 2>&1 &
PYTHON_PID=$!
echo "   PID: $PYTHON_PID"
sleep 2
echo ""

# Start Next.js dev server in background
echo "🚀 Starting Next.js dev server (port 3000)..."
cd "$REPO_DIR/web"
nohup npm run dev > nextjs.log 2>&1 &
NEXTJS_PID=$!
echo "   PID: $NEXTJS_PID"
sleep 3
echo ""

echo "✅ All services started!"
echo ""
echo "📍 Service URLs:"
echo "   • Next.js:  http://localhost:3000"
echo "   • FastAPI: http://localhost:8001/docs"
echo ""
echo "📋 Logs:"
echo "   • FastAPI:  data-layer/uvicorn.log"
echo "   • Next.js:  web/nextjs.log"
echo ""
echo "To stop services: pkill -f uvicorn && pkill -f 'next dev'"
