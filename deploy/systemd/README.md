# Systemd Deployment for AosiConn

This directory contains systemd service configuration for running AosiConn as a system service.

## Quick Install

```bash
# Run the install script as root
sudo ./deploy/systemd/install.sh
```

## Manual Installation

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Create User and Directories

```bash
sudo useradd --system --home-dir /opt/aosiconn --shell /bin/false aosiconn
sudo mkdir -p /opt/aosiconn/data/{db,logs,threads}
```

### 3. Copy Application Files

```bash
sudo cp -r core /opt/aosiconn/
sudo cp pyproject.toml uv.lock /opt/aosiconn/
sudo chown -R aosiconn:aosiconn /opt/aosiconn
```

### 4. Install Dependencies

```bash
cd /opt/aosiconn
sudo uv sync
```

### 5. Create Environment File

```bash
sudo nano /opt/aosiconn/.env
```

Add your configuration:
```
DATABASE_URL=sqlite:///db/aosiconn.db
JWT_SECRET_KEY=your-secret-key
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 6. Install Service

```bash
sudo cp deploy/systemd/aosiconn.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable aosiconn
sudo systemctl start aosiconn
```

## Service Management

### Check Status
```bash
sudo systemctl status aosiconn
```

### Start/Stop/Restart
```bash
sudo systemctl start aosiconn
sudo systemctl stop aosiconn
sudo systemctl restart aosiconn
```

### View Logs
```bash
# Follow logs
sudo journalctl -u aosiconn -f

# Last 100 lines
sudo journalctl -u aosiconn -n 100

# Since last boot
sudo journalctl -u aosiconn -b
```

## Troubleshooting

### Service fails to start

1. Check the logs: `sudo journalctl -u aosiconn -n 50`
2. Verify permissions: `sudo ls -la /opt/aosiconn/`
3. Test manually: `cd /opt/aosiconn/core/app && sudo -u aosiconn uv run python main.py`

### Permission Denied

Ensure the user has proper permissions:
```bash
sudo chown -R aosiconn:aosiconn /opt/aosiconn
sudo chmod 750 /opt/aosiconn/data
```

## Security Considerations

- The service runs as a non-privileged user (`aosiconn`)
- Uses systemd security hardening features
- Database and logs are isolated in `/opt/aosiconn/data/`
- Change the default JWT_SECRET_KEY in production
