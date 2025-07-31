# Setup Instructions

## Prerequisites

Make sure you have the following installed:
- Python 3.8+ (for backend)
- Node.js 16+ and npm (for frontend)
- pip (Python package manager)

## Quick Start

### Option 1: Use the project manager (Recommended)

```bash
# Start everything
./manage.sh start

# Check status
./manage.sh status

# Stop everything
./manage.sh stop

# View logs
./manage.sh logs
```

### Option 2: Use the startup script (macOS/Linux)

```bash
./start.sh
```

This will automatically install dependencies and start both servers.

### Option 3: Manual setup

#### 1. Setup Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Keep this terminal open. Backend will be available at `http://localhost:8000`

#### 2. Setup Frontend (in a new terminal)

```bash
cd frontend
npm install
npm start
```

Frontend will be available at `http://localhost:3000`

## First Run Test

1. Open your browser and go to `http://localhost:3000`
2. You should see the Text IDE interface with two panels
3. Click "Open Directory" 
4. Enter a path to a directory on your computer (e.g., `/Users/yourusername/Documents`)
5. The file tree should appear on the left
6. Click on any text file to open it in the editor on the right
7. Try editing the file - changes should save automatically

## Troubleshooting

### Backend Issues

- **Import errors for `magic` or `watchdog`**: Make sure all dependencies are installed with `pip install -r requirements.txt`
- **Permission errors**: Make sure the directory you're trying to open has read/write permissions
- **Port 8000 already in use**: Stop any other processes using port 8000 or change the port in `main.py`

### Frontend Issues

- **Dependencies not installing**: Try deleting `node_modules` and running `npm install` again
- **Port 3000 already in use**: React will automatically suggest a different port (like 3001)
- **CORS errors**: Make sure the backend is running on port 8000

### General Issues

- **WebSocket connection errors**: Make sure both backend and frontend are running and check your browser's developer console for errors
- **File changes not syncing**: Check the browser console and backend logs for any error messages

## Development Notes

### Backend Structure
- `main.py`: Main FastAPI application with all endpoints and WebSocket handling
- File system operations are handled with async/await for better performance
- Uses `watchdog` library to monitor file system changes
- `python-magic` for binary file detection

### Frontend Structure
- `App.tsx`: Main application component managing state and WebSocket connection
- `FileTree.tsx`: Left panel component for directory navigation
- `FileEditor.tsx`: Right panel component with Monaco Editor for code editing
- Uses Monaco Editor (VS Code's editor) for syntax highlighting and advanced editing features

### API Endpoints

- `POST /api/open-directory`: Opens a directory and returns file tree
- `GET /api/file-content?path=<path>`: Gets file content 
- `POST /api/write-file`: Saves file content
- `WS /ws`: WebSocket for real-time file synchronization

## Security Warning

This application is designed for local development use only. It provides direct file system access, so:

- Only run it on your local machine
- Don't expose it to the internet without proper security measures
- Be careful about which directories you open
- Consider running it in a sandboxed environment for sensitive work