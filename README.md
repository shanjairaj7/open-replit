# open-replit - LLM Agent Code Generation System

Open source replit altnernative using LLMs to generate backend and frontend code deploy full-stack applications automatically.

<img width="1009" height="496" alt="image" src="https://github.com/user-attachments/assets/35fa029f-90d5-40b1-bfb8-ea692029baf4" />

## 🏗️ System Architecture

It consists of three main layers:

### 1. **Template Layer** (Boilerplate)
- Frontend and backend templates that serve as the foundation for generated applications
- Located in `frontend-boilerplate-clone/` and `backend-boilerplate-clone/`
- Every generated app inherits from these templates

### 2. **Generation Layer** (LLM Agent)
- AI agent that customizes templates based on user requirements
- Creates unique, fully-functional applications for each user
- Manages code generation, editing, and terminal operations

### 3. **Infrastructure Layer**
- Azure Blob Storage for code persistence
- VM with public API for terminal command execution
- Modal.com for backend deployment
- Real-time streaming API for client communication

## 📊 Data Flow

```
User Request → LLM Agent → Code Generation → Azure Storage → VM Sync → Terminal Execution
                    ↓                              ↓                           ↓
              Streaming API ← Project Files ← File Updates ← Command Results
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Azure Storage Account
- VM with Ubuntu (for terminal API)
- Modal.com account (for backend deployment)
- OpenRouter API key (for LLM)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/bolt.diy.git
cd bolt.diy
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

3. **Install backend dependencies**
```bash
cd backend/api_server
pip install -r requirements.txt
```

4. **Install frontend dependencies**
```bash
cd ../../frontend
npm install
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory with the following:

```env
# LLM Configuration
OPENROUTER_API_KEY=your_openrouter_key
GROQ_API_KEY=your_groq_key  # Optional fallback

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
AZURE_STORAGE_CONTAINER=codebase-projects

# VM API Configuration
VM_API_BASE_URL=http://your-vm-ip:8000

# Modal Configuration
MODAL_APP_NAME=your-app-name
```

### Setting Up the VM Terminal API

1. **Deploy the VM API on your Ubuntu VM:**
```bash
# On your VM
cd vm-api
pip install -r requirements.txt
python app.py --host 0.0.0.0 --port 8000
```

2. **Configure firewall to allow port 8000:**
```bash
sudo ufw allow 8000
```

3. **Set up project directories:**
```bash
mkdir -p /home/ubuntu/projects
chmod 755 /home/ubuntu/projects
```

### Azure Storage Setup

1. **Create an Azure Storage Account**
2. **Create two containers:**
   - `codebase-projects` - For project files
   - `codebase-docs` - For documentation
3. **Get your connection string from Azure Portal**
4. **Add it to your `.env` file**

## 🏃 Running the System

### Start the Backend API Server
```bash
cd backend/api_server
python app.py
# API will be available at http://localhost:8000
```

### Start the Frontend Development Server
```bash
cd frontend
npm run dev
# Frontend will be available at http://localhost:5173
```

### Start the VM Terminal API (on your VM)
```bash
cd vm-api
python app.py --host 0.0.0.0 --port 8000
```

## 🔄 System Workflow

### 1. User Interaction
- User sends a request through the frontend chat interface
- Request includes project requirements and specifications

### 2. LLM Processing
- Agent analyzes the request using the configured LLM (OpenRouter/Groq)
- Generates a plan and starts creating/editing files

### 3. File Management
- Files are created/edited and stored in Azure Blob Storage
- Automatically synced to the VM for terminal operations

### 4. Terminal Operations
- Commands are executed on the VM through the Terminal API
- Results are streamed back to the user in real-time

### 5. Deployment
- Backend can be deployed to Modal.com
- Frontend can be deployed to Netlify/Vercel/Cloudflare

## 📁 Project Structure

```
bolt.diy/
├── backend/
│   ├── api_server/         # Main API server
│   │   ├── app.py          # FastAPI application
│   │   ├── streaming_api.py # WebSocket streaming
│   │   ├── agent_class.py  # LLM agent logic
│   │   ├── cloud_storage.py # Azure integration
│   │   └── vm_api.py       # VM terminal API client
│   ├── backend-boilerplate-clone/  # Backend template
│   └── frontend-boilerplate-clone/ # Frontend template
├── frontend/               # React frontend
├── vm-api/                # Terminal API for VM
└── .env.example           # Environment variables template
```

## 🛠️ Key Components

### Agent System (`agent_class.py`)
- Handles LLM interactions and code generation
- Manages file operations and terminal commands
- Implements retry logic and error handling

### Streaming API (`streaming_api.py`)
- WebSocket-based real-time communication
- Streams code changes and terminal output to frontend
- Manages conversation state and project tracking

### Cloud Storage (`cloud_storage.py`)
- Interfaces with Azure Blob Storage
- Handles file upload/download operations
- Manages project isolation and versioning

### VM API (`vm_api.py`)
- Client for terminal operations on VM
- Executes commands in project context
- Returns real-time command output

## 🔐 Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **VM Access**: Secure your VM with proper firewall rules
3. **Azure Storage**: Use SAS tokens for limited access when possible
4. **User Isolation**: Each project runs in isolated directories

## 🚧 Development

### Adding New Features
1. Update boilerplate templates for template-level features
2. Modify agent prompts for new capabilities
3. Extend VM API for additional terminal operations

### Testing
```bash
# Run backend tests
cd backend
pytest

# Run frontend tests
cd frontend
npm test
```

## 📝 API Documentation

### Main Endpoints

#### POST `/chat/stream`
Initiates a streaming chat session with the LLM agent.

#### GET `/projects/{project_id}/files`
Lists all files in a project.

#### POST `/projects/{project_id}/terminal`
Executes a terminal command in the project context.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

For issues and questions:
- Open an issue on GitHub
- Check the documentation in `/backend/llm_docs/`
- Review example implementations in the boilerplate folders

## 🎯 Roadmap

- [ ] Multi-model support (Claude, GPT-4, etc.)
- [ ] Enhanced security features
- [ ] Collaborative editing support
- [ ] Custom deployment targets
- [ ] Plugin system for extensions
