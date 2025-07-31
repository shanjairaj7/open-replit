import React, { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Upload, File, Plus, Save, Trash2, Edit3 } from 'lucide-react';

interface ExcelFile {
  id: string;
  name: string;
  data: any[][];
  headers: string[];
}

interface ExcelSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onDataUpdate: (data: any) => void;
}

export const ExcelSidebar: React.FC<ExcelSidebarProps> = ({ isOpen, onClose, onDataUpdate }) => {
  const [files, setFiles] = useState<ExcelFile[]>([]);
  const [activeFile, setActiveFile] = useState<ExcelFile | null>(null);
  const [editingCell, setEditingCell] = useState<{ row: number; col: number } | null>(null);
  const [editValue, setEditValue] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const data = new Uint8Array(e.target?.result as ArrayBuffer);
      // Simulated Excel parsing - in real app, use a library like xlsx
      const parsedData = simulateExcelParsing(data);
      
      const newFile: ExcelFile = {
        id: Date.now().toString(),
        name: file.name,
        data: parsedData.rows,
        headers: parsedData.headers,
      };
      
      setFiles(prev => [...prev, newFile]);
      setActiveFile(newFile);
    };
    reader.readAsArrayBuffer(file);
  };

  const simulateExcelParsing = (data: Uint8Array) => {
    // Simulated data for demo
    return {
      headers: ['Name', 'Age', 'Email', 'Department'],
      rows: [
        ['John Doe', 28, 'john@company.com', 'Engineering'],
        ['Jane Smith', 32, 'jane@company.com', 'Marketing'],
        ['Bob Johnson', 25, 'bob@company.com', 'Sales'],
        ['Alice Brown', 29, 'alice@company.com', 'HR'],
      ],
    };
  };

  const handleCellEdit = (row: number, col: number, value: string) => {
    if (!activeFile) return;
    
    const updatedFile = {
      ...activeFile,
      data: activeFile.data.map((r, i) => 
        i === row ? r.map((c, j) => j === col ? value : c) : r
      ),
    };
    
    setActiveFile(updatedFile);
    setFiles(files.map(f => f.id === updatedFile.id ? updatedFile : f));
  };

  const handleSaveChanges = () => {
    if (activeFile) {
      onDataUpdate({ file: activeFile.name, data: activeFile.data });
      console.log('Saving changes to:', activeFile.name);
    }
  };

  const handleCreateNewFile = () => {
    const newFile: ExcelFile = {
      id: Date.now().toString(),
      name: 'New File.xlsx',
      data: [['']],
      headers: ['Column 1', 'Column 2', 'Column 3', 'Column 4'],
    };
    
    setFiles(prev => [...prev, newFile]);
    setActiveFile(newFile);
  };

  const handleDeleteFile = (fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
    if (activeFile?.id === fileId) {
      setActiveFile(null);
    }
  };

  const startEdit = (row: number, col: number, value: string) => {
    setEditingCell({ row, col });
    setEditValue(value);
  };

  const finishEdit = () => {
    if (editingCell) {
      handleCellEdit(editingCell.row, editingCell.col, editValue);
      setEditingCell(null);
      setEditValue('');
    }
  };

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="left" className="w-96 max-w-full p-0">
        <SheetHeader className="p-6 border-b">
          <SheetTitle>Excel File Manager</SheetTitle>
        </SheetHeader>
        
        <div className="flex flex-col h-full">
          {/* Upload Section */}
          <div className="p-6 border-b space-y-4">
            <Button
              onClick={() => fileInputRef.current?.click()}
              className="w-full"
              variant="outline"
            >
              <Upload className="w-4 h-4 mr-2" />
              Upload Excel File
            </Button>
            <Input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls"
              onChange={handleFileUpload}
              className="hidden"
            />
            <Button
              onClick={handleCreateNewFile}
              className="w-full"
              variant="secondary"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create New File
            </Button>
          </div>

          {/* Files List */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-4">
              <h3 className="text-sm font-semibold mb-3">Uploaded Files</h3>
              <div className="space-y-2">
                {files.map((file) => (
                  <div
                    key={file.id}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      activeFile?.id === file.id
                        ? 'border-primary bg-primary/5'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => setActiveFile(file)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <File className="w-4 h-4 text-gray-500" />
                        <span className="text-sm font-medium">{file.name}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteFile(file.id);
                        }}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Excel Data Table */}
            {activeFile && (
              <div className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold">{activeFile.name}</h3>
                  <Button
                    size="sm"
                    onClick={handleSaveChanges}
                  >
                    <Save className="w-4 h-4 mr-2" />
                    Save
                  </Button>
                </div>
                
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {activeFile.headers.map((header, index) => (
                          <TableHead key={index} className="font-medium">
                            {header}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {activeFile.data.map((row, rowIndex) => (
                        <TableRow key={rowIndex}>
                          {row.map((cell, cellIndex) => (
                            <TableCell key={cellIndex}>
                              {editingCell?.row === rowIndex && editingCell?.col === cellIndex ? (
                                <Input
                                  value={editValue}
                                  onChange={(e) => setEditValue(e.target.value)}
                                  onBlur={finishEdit}
                                  onKeyPress={(e) => e.key === 'Enter' && finishEdit()}
                                  autoFocus
                                  className="h-8 text-sm"
                                />
                              ) : (
                                <div
                                  className="cursor-pointer hover:bg-muted/50 p-1 rounded"
                                  onClick={() => startEdit(rowIndex, cellIndex, cell)}
                                >
                                  {cell || '-'}
                                </div>
                              )}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
};