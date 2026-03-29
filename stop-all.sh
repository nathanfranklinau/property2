#!/bin/bash

echo "🛑 Stopping all services..."

# Kill Next.js
pkill -f "next dev" 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

# Kill Python FastAPI
pkill -f uvicorn 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true

echo "✅ All services stopped"
