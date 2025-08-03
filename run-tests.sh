#!/bin/bash

# Kill any processes running on our ports
lsof -ti:3000,8001 | xargs kill -9 2>/dev/null

# Start backend in background
cd backend
python main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend in background
cd ../frontend
npm start &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 5

# Run tests
npm run test:e2e:ui

# Cleanup on exit
trap 'kill $BACKEND_PID $FRONTEND_PID' EXIT