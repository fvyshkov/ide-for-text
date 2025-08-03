#!/bin/bash

echo "🚀 Starting Text IDE with AI Agent..."
echo "=================================================="

# Function to kill processes on specific ports
kill_port() {
    local port=$1
    local service_name=$2
    echo "🔍 Checking for processes on port $port..."
    
    # Find processes using the port
    local pids=$(lsof -ti:$port 2>/dev/null)
    
    if [ -n "$pids" ]; then
        echo "🛑 Killing existing $service_name processes on port $port..."
        for pid in $pids; do
            echo "   Killing PID: $pid"
            kill -9 $pid 2>/dev/null || true
        done
        sleep 1
    else
        echo "✅ Port $port is free"
    fi
}

# Function to check if a port is available
wait_for_port() {
    local port=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $service_name to start on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:$port" > /dev/null 2>&1; then
            echo "✅ $service_name is running on port $port"
            return 0
        fi
        
        if [ $((attempt % 5)) -eq 0 ]; then
            echo "   Still waiting... (attempt $attempt/$max_attempts)"
        fi
        
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service_name failed to start on port $port"
    return 1
}

# Cleanup function for graceful shutdown
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill_port 3000 "Frontend"
    kill_port 8001 "Backend"
    echo "👋 Goodbye!"
    exit 0
}

# Set up trap for Ctrl+C
trap cleanup INT TERM

echo "🧹 Cleaning up old processes..."
kill_port 8001 "Backend"
kill_port 3000 "Frontend"

echo ""
echo "🔧 Starting backend server..."
cd backend

# Install dependencies if needed
if [ ! -d "venv" ] && [ ! -f ".venv_created" ]; then
    echo "📦 Installing backend dependencies..."
    pip install -r requirements.txt
fi

# Start backend in background
python main.py &
BACKEND_PID=$!

# Wait for backend to be ready
if ! wait_for_port 8001 "Backend API"; then
    echo "❌ Backend failed to start"
    exit 1
fi

echo ""
echo "⚛️  Starting frontend server..."
cd ../frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

# Start frontend in background
npm start &
FRONTEND_PID=$!

# Wait for frontend to be ready
if ! wait_for_port 3000 "Frontend"; then
    echo "❌ Frontend failed to start"
    cleanup
    exit 1
fi

echo ""
echo "🎉 Text IDE is ready!"
echo "=================================================="
echo "🔗 Frontend: http://localhost:3000"
echo "🔗 Backend:  http://localhost:8001"
echo "🔗 API Docs: http://localhost:8001/docs"
echo ""
echo "💡 Features available:"
echo "   • AI Assistant with Claude 3.5 Sonnet"
echo "   • Transparent AI thinking process"
echo "   • File editing and project management"
echo "   • Copy messages functionality"
echo ""
echo "🛑 Press Ctrl+C to stop all services"
echo "=================================================="

# Keep script running and wait for shutdown
wait