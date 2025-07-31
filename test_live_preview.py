#!/usr/bin/env python3
"""
Test script for live preview functionality
"""
import requests
import time
import json

API_URL = "https://projects-api-production-e403.up.railway.app"
PROJECT_ID = "2ba5d793-7edc-4f14-af78-9cb2b17d5e71"  # Your existing project

def test_live_preview():
    print("🚀 Testing Live Preview System")
    print("=" * 50)
    
    # 1. Check project exists
    print("1️⃣ Checking project...")
    projects = requests.get(f"{API_URL}/api/projects").json()
    if not any(p['id'] == PROJECT_ID for p in projects['projects']):
        print("❌ Project not found!")
        return
    print("✅ Project found")
    
    # 2. Start preview server
    print("\n2️⃣ Starting preview server...")
    response = requests.post(f"{API_URL}/api/projects/{PROJECT_ID}/preview/start")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Preview server started on port {data['port']}")
        print(f"🌐 Preview URL: {API_URL}{data['preview_url']}")
    else:
        print(f"❌ Failed to start preview: {response.text}")
        return
    
    # 3. Test updating a file
    print("\n3️⃣ Testing file update...")
    new_dashboard_content = '''import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
          Live Preview Working! 🎉
        </h1>
        <p className="text-muted-foreground">This update happened in real-time!</p>
        <p className="text-sm text-blue-600 mt-2">Updated at: {new Date().toLocaleTimeString()}</p>
      </div>
      
      <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
        <CardHeader>
          <CardTitle>Live Preview Status</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold text-green-900">✅ Active</p>
          <p className="text-sm text-green-700">Changes appear instantly!</p>
        </CardContent>
      </Card>
    </div>
  )
}'''
    
    update_response = requests.post(
        f"{API_URL}/api/projects/{PROJECT_ID}/files/write",
        json={
            "file_path": "src/pages/Dashboard.tsx",
            "content": new_dashboard_content
        }
    )
    
    if update_response.status_code == 200:
        print("✅ File updated successfully")
        print("🔄 Vite should hot-reload automatically!")
    else:
        print(f"❌ Failed to update file: {update_response.text}")
    
    # 4. Show preview URL
    print("\n" + "=" * 50)
    print(f"🎯 Open this URL in your browser:")
    print(f"👉 {API_URL}/api/projects/{PROJECT_ID}/preview/")
    print("\n📝 Try editing files via the API - changes will appear instantly!")
    print("🛑 To stop the preview server, run:")
    print(f"   curl -X POST {API_URL}/api/projects/{PROJECT_ID}/preview/stop")

if __name__ == "__main__":
    test_live_preview()