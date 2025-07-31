#!/bin/bash

echo "Starting Text IDE Backend..."
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload