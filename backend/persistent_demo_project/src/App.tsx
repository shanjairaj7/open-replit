import React, { useState } from 'react';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { ExcelSidebar } from './components/ExcelSidebar';
import { Button } from '@/components/ui/button';
import { Menu } from 'lucide-react';

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const handleExcelDataUpdate = (data: any) => {
    console.log('Excel data updated:', data);
    // Here you can integrate the Excel data with your dashboard
    // For example: update dashboard state or trigger analytics recalculation
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="flex h-screen">
        <div className="flex-1 flex flex-col">
          <header className="bg-white shadow-sm border-b px-4 py-3">
            <div className="flex items-center justify-between">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsSidebarOpen(true)}
                className="lg:hidden"
              >
                <Menu className="h-4 w-4" />
              </Button>
              <h1 className="text-xl font-semibold text-gray-900">Analytics Dashboard</h1>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsSidebarOpen(true)}
                className="hidden lg:flex items-center space-x-2"
              >
                <Menu className="h-4 w-4" />
                <span>Excel Manager</span>
              </Button>
            </div>
          </header>
          
          <main className="flex-1 overflow-auto p-6">
            <AnalyticsDashboard />
          </main>
        </div>
      </div>

      <ExcelSidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        onDataUpdate={handleExcelDataUpdate}
      />
    </div>
  );
}

export default App;