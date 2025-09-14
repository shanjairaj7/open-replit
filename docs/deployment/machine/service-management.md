# VM Service Management Guide

## Service Commands

### Stop Services
```bash
# Stop both services
sudo systemctl stop llm-workers.service
sudo systemctl stop llm-api.service

# Kill any remaining processes (backup method)
pkill -f worker.py
pkill -f api.py
```

### Start Services
```bash
# Start both services
sudo systemctl start llm-api.service
sudo systemctl start llm-workers.service

# Or restart if already running
sudo systemctl restart llm-api.service
sudo systemctl restart llm-workers.service
```

### Check Service Status
```bash
# Check if services are running
sudo systemctl status llm-api.service
sudo systemctl status llm-workers.service

# Quick active check
sudo systemctl is-active llm-api.service
sudo systemctl is-active llm-workers.service

# Check running processes
ps aux | grep -E "(api.py|worker.py)" | grep -v grep
```

### View Logs
```bash
# View recent logs
sudo journalctl -u llm-api.service -n 20
sudo journalctl -u llm-workers.service -n 20

# Follow logs in real-time
sudo journalctl -u llm-api.service -f
sudo journalctl -u llm-workers.service -f

# View all logs since boot
sudo journalctl -u llm-api.service
sudo journalctl -u llm-workers.service
```

## Full Restart Sequence (After Code Updates)

```bash
# 1. Stop services
sudo systemctl stop llm-workers.service
sudo systemctl stop llm-api.service

# 2. Kill any remaining processes
pkill -f worker.py
pkill -f api.py

# 3. Wait a moment
sleep 2

# 4. Reload systemd (if service files changed)
sudo systemctl daemon-reload

# 5. Start services
sudo systemctl start llm-api.service
sudo systemctl start llm-workers.service

# 6. Check status
sudo systemctl status llm-api.service
sudo systemctl status llm-workers.service

# 7. Verify processes are running
ps aux | grep -E "(api.py|worker.py)" | grep -v grep
```

## Service File Locations

- **API Service**: `/etc/systemd/system/llm-api.service`
- **Worker Service**: `/etc/systemd/system/llm-workers.service`
- **Code Directory**: `/home/azureuser/llm_agent_backend/`

## Troubleshooting

### Services Won't Start
```bash
# Check detailed status
sudo systemctl status llm-api.service -l
sudo systemctl status llm-workers.service -l

# Check logs for errors
sudo journalctl -u llm-api.service -n 50
sudo journalctl -u llm-workers.service -n 50
```

### Services Keep Restarting
```bash
# Check if files exist and have correct permissions
ls -la /home/azureuser/llm_agent_backend/
ls -la /home/azureuser/llm_agent_backend/venv/bin/python

# Test manual execution
cd /home/azureuser/llm_agent_backend
source venv/bin/activate
python api.py  # Should start without errors
python worker.py  # Should start without errors
```

### Port Already in Use
```bash
# Check what's using port 8000
sudo netstat -tlnp | grep :8000
sudo ss -tlnp | grep :8000

# Kill process using port 8000
sudo kill -9 <PID>
```

## API Health Check

After restarting services, verify they're working:

```bash
# Test API health endpoint
curl "http://llm-agent-api.eastus.cloudapp.azure.com:8000/health"

# Expected response:
# {"status":"healthy","queue":"connected","azure_storage":"connected"}
```

## Manual Service Start (Without Systemd)

If systemd services aren't working, you can start manually:

```bash
# Terminal 1: Start API
cd /home/azureuser/llm_agent_backend
source venv/bin/activate
python api.py

# Terminal 2: Start Workers (3 workers)
cd /home/azureuser/llm_agent_backend
source venv/bin/activate
for i in {1..3}; do
    nohup python worker.py > worker_$i.log 2>&1 &
done
```

## Free Up VM Memory (Kill Zed Processes)

Zed editor remote connections consume significant VM memory. Kill these processes to free up resources:

```bash
# Kill all Zed-related processes
pkill -f zed-remote-server
pkill -f tsserver
pkill -f tailwindcss-language-server
pkill -f pyright
pkill -f pylsp
pkill -f json-language-server
pkill -f vscode-langservers-extracted

# Kill all Node.js language servers (more aggressive)
pkill -f "node.*language"
pkill -f "node.*langserver"

# One-liner to kill all common language servers
pkill -f "zed-remote-server|tsserver|tailwindcss-language-server|pyright|pylsp|json-language-server|vscode-langservers"
```

### Check Memory Usage
```bash
# Before killing processes
free -h

# Check what processes are using most memory
ps aux --sort=-%mem | head -10

# After killing processes
free -h
```

### Verify Zed Processes Are Gone
```bash
# Should return no results after killing
ps aux | grep -E "(zed|tsserver|tailwind|pyright|pylsp)" | grep -v grep
```

## Service Auto-Start on Boot

Services are configured to start automatically on boot. To disable/enable:

```bash
# Disable auto-start
sudo systemctl disable llm-api.service
sudo systemctl disable llm-workers.service

# Enable auto-start
sudo systemctl enable llm-api.service
sudo systemctl enable llm-workers.service
```

## Complete VM Cleanup & Restart Sequence

For maximum performance after code changes:

```bash
# 1. Kill all Zed processes (frees ~1GB+ RAM)
pkill -f "zed-remote-server|tsserver|tailwindcss-language-server|pyright|pylsp|json-language-server|vscode-langservers"

# 2. Stop services
sudo systemctl stop llm-workers.service
sudo systemctl stop llm-api.service

# 3. Kill any remaining processes
pkill -f worker.py
pkill -f api.py

# 4. Check memory is freed
free -h

# 5. Wait and reload
sleep 3
sudo systemctl daemon-reload

# 6. Start services
sudo systemctl start llm-api.service
sudo systemctl start llm-workers.service

# 7. Verify everything is working
curl "http://llm-agent-api.eastus.cloudapp.azure.com:8000/health"
```