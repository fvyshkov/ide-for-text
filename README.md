# Text IDE

A web-based text editor for local files built with FastAPI and React.

## Features

- **File Tree**: Browse and open local directories
- **Text Editor**: Edit text files with syntax highlighting  
- **AI Chat Integration**: Advanced AI-powered data analysis and processing
- **Real-time Sync**: Changes are automatically saved to disk
- **WebSocket Support**: Real-time synchronization between app and file system
- **Binary File Detection**: Identifies and handles binary files appropriately
- **Theme Support**: Light and dark mode with user preference persistence
- **Resizable Panels**: Flexible three-panel layout with adjustable splitters

## 📚 Documentation

For detailed technical documentation, architecture guides, and implementation details, see the **[Documentation](./docs/)** folder:

- **[Prompt Processing Workflow](./docs/prompt-processing-workflow.md)** - Complete AI workflow documentation
- **[Documentation Index](./docs/README.md)** - Full documentation overview

## Project Structure

```
ide-for-text/
├── backend/          # FastAPI backend
│   ├── main.py       # Main application file
│   └── requirements.txt
├── frontend/         # React + TypeScript frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── FileTree.tsx
│   │   │   ├── FileEditor.tsx
│   │   │   ├── AIChat.tsx
│   │   │   ├── TripleSplitter.tsx
│   │   │   └── *.css
│   │   ├── contexts/
│   │   │   └── ThemeContext.tsx
│   │   ├── App.tsx
│   │   ├── types.ts
│   │   └── index.tsx
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
├── docs/             # Technical documentation
│   ├── README.md     # Documentation index
│   └── prompt-processing-workflow.md  # AI workflow guide
├── manage.sh         # Universal project manager (start/stop/status/logs)
├── run-backend.sh    # Individual backend starter
├── run-frontend.sh   # Individual frontend starter
├── start.sh          # Legacy combined starter
└── README.md
```

## Setup and Running

### Quick Start

Use the universal project manager script:

```bash
# Start everything (backend + frontend)
./manage.sh start

# Or simply (start is default)
./manage.sh

# Stop everything
./manage.sh stop

# Restart everything
./manage.sh restart

# Check status
./manage.sh status

# View logs
./manage.sh logs
```

### Alternative: Individual Scripts

You can also start services separately:

```bash
# Start backend (in terminal 1)
./run-backend.sh

# Start frontend (in terminal 2)
./run-frontend.sh
```

### Manual Setup

#### Backend (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the backend server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8001 --reload
   ```

   The backend will be available at `http://localhost:8001`

### Frontend (React)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

   The frontend will be available at `http://localhost:3000`

## Usage

1. Start the application: `./manage.sh start`
2. Open `http://localhost:3000` in your browser
3. Click "Open Directory" and enter a local directory path (try `./test-directory`)
4. Browse the file tree on the left panel
5. Click on any text file to open it in the editor
6. Make changes - they'll be automatically saved to disk
7. Use "Refresh" to reload the file tree if files change externally
8. Stop the application: `./manage.sh stop`

## API Endpoints

### REST API

- `POST /api/open-directory` - Open a directory and get file tree
- `GET /api/file-content?path=<file_path>` - Get file content
- `POST /api/write-file` - Write content to a file

### WebSocket

- `WS /ws` - Real-time file synchronization

## Features in Detail

### File Tree
- Displays hierarchical directory structure
- Expandable/collapsible folders
- File type icons
- Selection highlighting

### Text Editor
- Syntax highlighting for many languages
- Line numbers and minimap
- Auto-indentation and formatting
- Real-time saving

### Real-time Sync
- Changes in the editor are immediately saved to disk
- External file changes are detected and reflected in the editor
- WebSocket-based communication for instant updates

## Development

### Dependencies

**Backend:**
- FastAPI: Web framework
- aiofiles: Async file operations
- python-magic: File type detection
- watchdog: File system monitoring
- WebSockets: Real-time communication

**Frontend:**
- React 18: UI framework
- TypeScript: Type safety
- Monaco Editor: Code editor component
- React Icons: Icon library

## Security Notes

This application is designed for local development use. For production deployment:
- Add authentication and authorization
- Implement file access restrictions
- Add HTTPS support
- Validate and sanitize all file paths
- Add rate limiting