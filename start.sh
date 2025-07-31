#!/bin/bash

echo "Starting Text IDE..."

# Start backend
echo "Starting backend server..."
cd backend
pip install -r requirements.txt
python main.py &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 3

# Start frontend in new terminal/tab
echo "Starting frontend server..."
cd ../frontend
npm install
npm start &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Backend available at: http://localhost:8001"
echo "Frontend available at: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for user input to stop
wait