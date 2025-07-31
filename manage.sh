#!/bin/bash

# Text IDE Project Manager
# Usage: ./manage.sh [start|stop|restart|status]

PROJECT_NAME="Text IDE"
BACKEND_PORT=8001
FRONTEND_PORT=3000

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${BLUE}[${PROJECT_NAME}]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[${PROJECT_NAME}]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[${PROJECT_NAME}]${NC} $1"
}

print_error() {
    echo -e "${RED}[${PROJECT_NAME}]${NC} $1"
}

# Function to check if port is in use
is_port_in_use() {
    lsof -i :$1 > /dev/null 2>&1
    return $?
}

# Function to get PID using a port
get_pid_by_port() {
    lsof -ti :$1 2>/dev/null
}

# Function to stop processes
stop_services() {
    print_message "Stopping all services..."
    
    # Stop backend (uvicorn)
    backend_pid=$(get_pid_by_port $BACKEND_PORT)
    if [ ! -z "$backend_pid" ]; then
        print_message "Stopping backend (PID: $backend_pid)..."
        kill $backend_pid 2>/dev/null
        sleep 2
        
        # Force kill if still running
        if kill -0 $backend_pid 2>/dev/null; then
            print_warning "Force killing backend..."
            kill -9 $backend_pid 2>/dev/null
        fi
        print_success "Backend stopped"
    else
        print_message "Backend not running"
    fi
    
    # Stop frontend (npm/react)
    frontend_pid=$(get_pid_by_port $FRONTEND_PORT)
    if [ ! -z "$frontend_pid" ]; then
        print_message "Stopping frontend (PID: $frontend_pid)..."
        kill $frontend_pid 2>/dev/null
        sleep 2
        
        # Force kill if still running
        if kill -0 $frontend_pid 2>/dev/null; then
            print_warning "Force killing frontend..."
            kill -9 $frontend_pid 2>/dev/null
        fi
        print_success "Frontend stopped"
    else
        print_message "Frontend not running"
    fi
    
    # Kill any remaining node processes (React dev server)
    pkill -f "react-scripts" 2>/dev/null
    pkill -f "npm start" 2>/dev/null
    
    print_success "All services stopped"
}

# Function to start services
start_services() {
    print_message "Starting all services..."
    
    # Check if ports are already in use
    if is_port_in_use $BACKEND_PORT; then
        print_error "Backend port $BACKEND_PORT is already in use!"
        return 1
    fi
    
    if is_port_in_use $FRONTEND_PORT; then
        print_error "Frontend port $FRONTEND_PORT is already in use!"
        return 1
    fi
    
    # Start backend
    print_message "Starting backend on port $BACKEND_PORT..."
    cd backend
    
    # Install backend dependencies if needed
    if [ ! -d "__pycache__" ] || [ ! -f ".deps_installed" ]; then
        print_message "Installing backend dependencies..."
        pip install -r requirements.txt > /dev/null 2>&1
        touch .deps_installed
    fi
    
    # Start uvicorn in background
    nohup uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > ../backend.log 2>&1 &
    backend_pid=$!
    cd ..
    
    # Wait for backend to start
    print_message "Waiting for backend to start..."
    for i in {1..10}; do
        if is_port_in_use $BACKEND_PORT; then
            print_success "Backend started (PID: $backend_pid)"
            break
        fi
        sleep 1
        if [ $i -eq 10 ]; then
            print_error "Backend failed to start!"
            return 1
        fi
    done
    
    # Start frontend
    print_message "Starting frontend on port $FRONTEND_PORT..."
    cd frontend
    
    # Install frontend dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_message "Installing frontend dependencies..."
        npm install > /dev/null 2>&1
    fi
    
    # Start React dev server in background
    nohup npm start > ../frontend.log 2>&1 &
    frontend_pid=$!
    cd ..
    
    # Wait for frontend to start
    print_message "Waiting for frontend to start..."
    for i in {1..20}; do
        if is_port_in_use $FRONTEND_PORT; then
            print_success "Frontend started (PID: $frontend_pid)"
            break
        fi
        sleep 1
        if [ $i -eq 20 ]; then
            print_error "Frontend failed to start!"
            return 1
        fi
    done
    
    print_success "All services started successfully!"
    echo ""
    print_message "Backend:  http://localhost:$BACKEND_PORT"
    print_message "Frontend: http://localhost:$FRONTEND_PORT"
    echo ""
    print_message "Logs:"
    print_message "  Backend:  tail -f backend.log"
    print_message "  Frontend: tail -f frontend.log"
    echo ""
    print_message "To stop services: ./manage.sh stop"
}

# Function to check status
check_status() {
    print_message "Checking service status..."
    echo ""
    
    # Check backend
    if is_port_in_use $BACKEND_PORT; then
        backend_pid=$(get_pid_by_port $BACKEND_PORT)
        print_success "✓ Backend running (PID: $backend_pid, Port: $BACKEND_PORT)"
    else
        print_error "✗ Backend not running"
    fi
    
    # Check frontend
    if is_port_in_use $FRONTEND_PORT; then
        frontend_pid=$(get_pid_by_port $FRONTEND_PORT)
        print_success "✓ Frontend running (PID: $frontend_pid, Port: $FRONTEND_PORT)"
    else
        print_error "✗ Frontend not running"
    fi
    
    echo ""
}

# Function to show logs
show_logs() {
    print_message "Showing recent logs..."
    echo ""
    
    if [ -f "backend.log" ]; then
        echo -e "${BLUE}=== Backend Logs ===${NC}"
        tail -20 backend.log
        echo ""
    fi
    
    if [ -f "frontend.log" ]; then
        echo -e "${BLUE}=== Frontend Logs ===${NC}"
        tail -20 frontend.log
        echo ""
    fi
}

# Main script logic
case "${1:-start}" in
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        stop_services
        sleep 2
        start_services
        ;;
    "status")
        check_status
        ;;
    "logs")
        show_logs
        ;;
    *)
        echo "Usage: $0 [start|stop|restart|status|logs]"
        echo ""
        echo "Commands:"
        echo "  start   - Start both backend and frontend services"
        echo "  stop    - Stop all running services"
        echo "  restart - Stop and then start all services"
        echo "  status  - Check if services are running"
        echo "  logs    - Show recent log output"
        echo ""
        echo "Default command: start"
        exit 1
        ;;
esac