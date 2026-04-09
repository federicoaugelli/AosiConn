#!/bin/bash
# AosiConn Systemd Service Installation Script
# This script installs the AosiConn trading platform as a systemd service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/aosiconn"
SERVICE_USER="aosiconn"
SERVICE_NAME="aosiconn"

print_status() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_uv() {
    if ! command -v uv &> /dev/null; then
        print_error "uv is not installed. Please install uv first:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    print_status "uv is installed"
}

create_user() {
    if id "$SERVICE_USER" &>/dev/null; then
        print_warning "User $SERVICE_USER already exists"
    else
        print_status "Creating user $SERVICE_USER"
        useradd --system --home-dir "$INSTALL_DIR" --shell /bin/false "$SERVICE_USER"
    fi
}

setup_directories() {
    print_status "Setting up directories"
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    
    # Create data directories
    mkdir -p "$INSTALL_DIR/data/db"
    mkdir -p "$INSTALL_DIR/data/logs"
    mkdir -p "$INSTALL_DIR/data/threads"
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
}

copy_files() {
    print_status "Copying application files"
    
    # Get the directory where this script is located
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    
    # Copy project files
    cp -r "$PROJECT_ROOT/core" "$INSTALL_DIR/"
    cp "$PROJECT_ROOT/pyproject.toml" "$INSTALL_DIR/"
    cp "$PROJECT_ROOT/uv.lock" "$INSTALL_DIR/" 2>/dev/null || print_warning "No uv.lock found, will create during install"
    cp "$PROJECT_ROOT/.python-version" "$INSTALL_DIR/" 2>/dev/null || true
    
    # Create default .env if not exists
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        print_status "Creating default .env file"
        cat > "$INSTALL_DIR/.env" << 'EOF'
# AosiConn Environment Configuration
# Database
DATABASE_URL=sqlite:///db/aosiconn.db

# JWT Secret (CHANGE THIS IN PRODUCTION!)
JWT_SECRET_KEY=your-secret-key-change-this-in-production

# CORS Settings
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Log Level
LOG_LEVEL=INFO
EOF
    fi
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
}

install_dependencies() {
    print_status "Installing dependencies with uv"
    
    cd "$INSTALL_DIR"
    
    # Ensure uv is available
    export PATH="/root/.local/bin:$PATH"
    
    # Sync dependencies
    uv sync --frozen || uv sync
}

install_service() {
    print_status "Installing systemd service"
    
    # Get the directory where this script is located
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Copy service file
    cp "$SCRIPT_DIR/aosiconn.service" /etc/systemd/system/
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable service
    systemctl enable aosiconn.service
}

print_completion() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  AosiConn Installation Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Installation directory: $INSTALL_DIR"
    echo ""
    echo "Next steps:"
    echo "  1. Edit the environment file:"
    echo "     sudo nano $INSTALL_DIR/.env"
    echo ""
    echo "  2. Start the service:"
    echo "     sudo systemctl start aosiconn"
    echo ""
    echo "  3. Check service status:"
    echo "     sudo systemctl status aosiconn"
    echo ""
    echo "  4. View logs:"
    echo "     sudo journalctl -u aosiconn -f"
    echo ""
    echo "The API will be available at: http://localhost:8000"
    echo "Dashboard: http://localhost:8000/dashboard"
    echo ""
    print_warning "Remember to change JWT_SECRET_KEY in $INSTALL_DIR/.env"
}

# Main installation flow
main() {
    echo "========================================"
    echo "  AosiConn Trading Platform Installer"
    echo "========================================"
    echo ""
    
    check_root
    check_uv
    create_user
    setup_directories
    copy_files
    install_dependencies
    install_service
    
    print_completion
}

main "$@"
