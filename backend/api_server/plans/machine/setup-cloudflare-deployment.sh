#!/bin/bash
# Setup script for Cloudflare Pages deployment on VM

echo "🚀 Setting up Cloudflare Pages deployment on VM..."

# Check if running as root/sudo
if [ "$EUID" -eq 0 ]; then
  echo "ℹ️  Running with sudo privileges"
fi

# Install Node.js 18 if not present
if ! command -v node &> /dev/null; then
    echo "📦 Installing Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
else
    echo "✅ Node.js already installed: $(node --version)"
fi

# Install npm if not present
if ! command -v npm &> /dev/null; then
    echo "📦 Installing npm..."
    sudo apt-get install -y npm
else
    echo "✅ npm already installed: $(npm --version)"
fi

# Install Wrangler globally
echo "🔧 Installing Wrangler CLI..."
sudo npm install -g wrangler@latest

# Verify installation
echo "🔍 Verifying installations..."
echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"
echo "Wrangler version: $(wrangler --version)"

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install python-dotenv

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Copy .env.example to .env"
echo "2. Add your Cloudflare API token and Account ID to .env"
echo "3. Restart the API and worker services"
echo ""
echo "🔗 Get Cloudflare credentials:"
echo "   API Token: https://dash.cloudflare.com/profile/api-tokens"
echo "   Account ID: Found in your Cloudflare dashboard sidebar"
echo ""
echo "📋 .env file should contain:"
echo "   CLOUDFLARE_API_TOKEN=your-token-here"
echo "   CLOUDFLARE_ACCOUNT_ID=your-account-id-here"