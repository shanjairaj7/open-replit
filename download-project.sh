#!/bin/bash

# Download Client Management System from Railway API

PROJECT_ID="2ba5d793-7edc-4f14-af78-9cb2b17d5e71"
API_URL="https://projects-api-production-e403.up.railway.app"
LOCAL_DIR="client-management-system"

echo "🔄 Downloading Client Management System..."

# Create directory
mkdir -p $LOCAL_DIR

# Key files to download
FILES=(
  "package.json"
  "vite.config.ts"
  "tsconfig.json"
  "index.html"
  "src/main.tsx"
  "src/App.tsx"
  "src/index.css"
  "src/types/index.ts"
  "src/lib/utils.ts"
  "src/hooks/useDebounce.ts"
  "src/hooks/useLocalStorage.ts"
  "src/components/app-sidebar.tsx"
  "src/components/ui/card.tsx"
  "src/components/ui/button.tsx"
  "src/components/ui/badge.tsx"
  "src/components/ui/progress.tsx"
  "src/components/ui/data-table.tsx"
  "src/components/ui/status-badge.tsx"
  "src/pages/Dashboard.tsx"
  "src/pages/Leads.tsx"
  "src/pages/Projects.tsx"
  "src/pages/Clients.tsx"
  "src/pages/Invoices.tsx"
  "src/pages/Reports.tsx"
)

# Download each file
for file in "${FILES[@]}"; do
  echo "📥 Downloading $file..."
  
  # Create directory if needed
  dir=$(dirname "$LOCAL_DIR/$file")
  mkdir -p "$dir"
  
  # Download file
  curl -s -X POST "$API_URL/api/projects/$PROJECT_ID/files/read" \
    -H "Content-Type: application/json" \
    -d "{\"file_path\": \"$file\"}" | \
    jq -r '.content' > "$LOCAL_DIR/$file"
done

echo "✅ Download complete!"
echo ""
echo "📦 To run the project:"
echo "cd $LOCAL_DIR"
echo "npm install"
echo "npm run dev"
echo ""
echo "Then open http://localhost:5173 in your browser"