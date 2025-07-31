import { useState, useCallback } from 'react';
import type { FileMap } from '~/lib/stores/files';

interface ValidationError {
  type: 'error' | 'warning';
  file: string;
  line?: number;
  message: string;
}

interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
}

export function usePreviewValidation() {
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);

  const validateTailwindClasses = (content: string, filePath: string): ValidationError[] => {
    const errors: ValidationError[] = [];
    
    // Extract className attributes
    const classNameRegex = /className\s*=\s*["']([^"']+)["']/g;
    let match;
    let lineNumber = 1;
    
    while ((match = classNameRegex.exec(content)) !== null) {
      const classes = match[1].split(' ');
      
      // Count line number
      lineNumber = content.substring(0, match.index).split('\n').length;
      
      for (const cssClass of classes) {
        // Skip dynamic classes
        if (cssClass.includes('${') || cssClass.includes('{')) continue;
        
        // Basic validation for common Tailwind patterns
        const validPatterns = [
          /^(m|p|w|h|text|bg|border|rounded|flex|grid|gap|space)[-:]/,
          /^(absolute|relative|fixed|static|sticky)$/,
          /^(block|inline|inline-block|hidden)$/,
          /^[a-z]+-\d+$/,  // numeric utilities like p-4, m-2
          /^[a-z]+-[a-z]+-\d+$/,  // color utilities like bg-blue-500
        ];
        
        const isValid = validPatterns.some(pattern => pattern.test(cssClass));
        
        if (!isValid && !cssClass.startsWith('!')) {
          errors.push({
            type: 'warning',
            file: filePath,
            line: lineNumber,
            message: `Potentially invalid Tailwind class: "${cssClass}"`
          });
        }
      }
    }
    
    return errors;
  };

  const validateTypeScript = (content: string, filePath: string): ValidationError[] => {
    const errors: ValidationError[] = [];
    
    // Check for common TypeScript/React errors
    const errorPatterns = [
      {
        pattern: /useState\s*\(\s*\)/g,
        message: 'useState requires an initial value or undefined'
      },
      {
        pattern: /useEffect\s*\(\s*\)/g,
        message: 'useEffect requires at least one argument'
      },
      {
        pattern: /export\s+default\s+function\s*\(\)/g,
        message: 'Component function needs a name'
      }
    ];
    
    for (const { pattern, message } of errorPatterns) {
      let match;
      while ((match = pattern.exec(content)) !== null) {
        const lineNumber = content.substring(0, match.index).split('\n').length;
        errors.push({
          type: 'error',
          file: filePath,
          line: lineNumber,
          message
        });
      }
    }
    
    // Check for unmatched brackets
    const brackets = [
      { open: '(', close: ')' },
      { open: '[', close: ']' },
      { open: '{', close: '}' }
    ];
    
    for (const { open, close } of brackets) {
      const openCount = (content.match(new RegExp('\\' + open, 'g')) || []).length;
      const closeCount = (content.match(new RegExp('\\' + close, 'g')) || []).length;
      
      if (openCount !== closeCount) {
        errors.push({
          type: 'error',
          file: filePath,
          message: `Unmatched ${open}${close} brackets: ${openCount} opening, ${closeCount} closing`
        });
      }
    }
    
    return errors;
  };

  const validateImports = (content: string, filePath: string, allFiles: FileMap): ValidationError[] => {
    const errors: ValidationError[] = [];
    
    // Extract import statements
    const importRegex = /import\s+.*?\s+from\s+["']([^"']+)["']/g;
    let match;
    
    while ((match = importRegex.exec(content)) !== null) {
      const importPath = match[1];
      const lineNumber = content.substring(0, match.index).split('\n').length;
      
      // Skip node_modules imports
      if (!importPath.startsWith('.') && !importPath.startsWith('@/')) {
        continue;
      }
      
      // Convert import path to file path
      let resolvedPath = importPath;
      if (importPath.startsWith('@/')) {
        resolvedPath = importPath.replace('@/', 'src/');
      } else if (importPath.startsWith('./')) {
        // Relative to current file
        const currentDir = filePath.substring(0, filePath.lastIndexOf('/'));
        resolvedPath = currentDir + '/' + importPath.substring(2);
      }
      
      // Check if file exists (try common extensions)
      const extensions = ['', '.ts', '.tsx', '.js', '.jsx', '/index.ts', '/index.tsx'];
      let found = false;
      
      for (const ext of extensions) {
        if (allFiles[resolvedPath + ext]) {
          found = true;
          break;
        }
      }
      
      if (!found) {
        errors.push({
          type: 'error',
          file: filePath,
          line: lineNumber,
          message: `Cannot resolve import: ${importPath}`
        });
      }
    }
    
    return errors;
  };

  const validateFiles = useCallback(async (files: FileMap): Promise<ValidationResult> => {
    setIsValidating(true);
    const allErrors: ValidationError[] = [];
    
    try {
      for (const [filePath, fileContent] of Object.entries(files)) {
        if (!fileContent?.content) continue;
        
        const content = fileContent.content;
        
        // Validate based on file type
        if (filePath.endsWith('.tsx') || filePath.endsWith('.jsx')) {
          // Validate TypeScript/React
          allErrors.push(...validateTypeScript(content, filePath));
          
          // Validate Tailwind classes
          allErrors.push(...validateTailwindClasses(content, filePath));
          
          // Validate imports
          allErrors.push(...validateImports(content, filePath, files));
        } else if (filePath.endsWith('.ts') || filePath.endsWith('.js')) {
          // Validate TypeScript
          allErrors.push(...validateTypeScript(content, filePath));
          
          // Validate imports
          allErrors.push(...validateImports(content, filePath, files));
        } else if (filePath === 'package.json') {
          // Validate package.json
          try {
            JSON.parse(content);
          } catch (e) {
            allErrors.push({
              type: 'error',
              file: filePath,
              message: `Invalid JSON: ${(e as Error).message}`
            });
          }
        }
      }
      
      const errors = allErrors.filter(e => e.type === 'error');
      const warnings = allErrors.filter(e => e.type === 'warning');
      
      const result: ValidationResult = {
        isValid: errors.length === 0,
        errors,
        warnings
      };
      
      setValidationResult(result);
      return result;
      
    } finally {
      setIsValidating(false);
    }
  }, []);

  const clearValidation = useCallback(() => {
    setValidationResult(null);
  }, []);

  return {
    validateFiles,
    clearValidation,
    isValidating,
    validationResult
  };
}