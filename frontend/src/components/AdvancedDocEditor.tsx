'use client';

import React, { useState, useEffect, forwardRef, useImperativeHandle, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Loader2, Save, RefreshCw } from 'lucide-react';
import { Card } from '@/components/ui/card';
import mammoth from 'mammoth';

// Simple toolbar component
const SimpleToolbar = ({ onAction }) => {
  const actions = [
    { name: 'bold', label: 'Bold', command: 'bold' },
    { name: 'italic', label: 'Italic', command: 'italic' },
    { name: 'underline', label: 'Underline', command: 'underline' },
    { name: 'h1', label: 'H1', command: 'formatBlock', value: '<h1>' },
    { name: 'h2', label: 'H2', command: 'formatBlock', value: '<h2>' },
    { name: 'h3', label: 'H3', command: 'formatBlock', value: '<h3>' },
    { name: 'p', label: 'P', command: 'formatBlock', value: '<p>' },
    { name: 'ul', label: 'Bullet List', command: 'insertUnorderedList' },
    { name: 'ol', label: 'Number List', command: 'insertOrderedList' },
  ];

  return (
    <div className="border-b p-2 flex flex-wrap gap-1 bg-white sticky top-0 z-10">
      {actions.map((action) => (
        <Button
          key={action.name}
          variant="outline"
          size="sm"
          onClick={() => onAction(action.command, action.value)}
          className="h-8 px-2 min-w-[40px]"
        >
          {action.label}
        </Button>
      ))}
    </div>
  );
};

interface AdvancedDocEditorProps {
  documentUrl?: string;
  onSave?: (content: string) => Promise<void>;
  readOnly?: boolean;
  className?: string;
}

export interface AdvancedDocEditorRef {
  getContent: () => string;
  setContent: (content: string) => void;
  getHtml: () => string;
}

const AdvancedDocEditor = forwardRef<AdvancedDocEditorRef, AdvancedDocEditorProps>(({
  documentUrl,
  onSave,
  readOnly = false,
  className = '',
}, ref) => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const editorRef = useRef<HTMLDivElement>(null);

  // Expose methods to parent component via ref
  useImperativeHandle(ref, () => ({
    getContent: () => content,
    setContent: (newContent: string) => {
      setContent(newContent);
      if (editorRef.current) {
        editorRef.current.innerHTML = newContent;
      }
    },
    getHtml: () => {
      if (editorRef.current) {
        return editorRef.current.innerHTML;
      }
      return content;
    }
  }));

  // Load document content when URL changes
  useEffect(() => {
    if (documentUrl) {
      loadDocument(documentUrl);
    }
  }, [documentUrl]);

  // Helper function to detect binary content
  const isBinaryContent = (content: string): boolean => {
    // Check for common binary file signatures
    const binarySignatures = [
      'PK\u0003\u0004', // ZIP/DOCX/XLSX
      '\u00D0\u00CF\u0011\u00E0', // MS Office old format
      '%PDF', // PDF
      '\u00FF\u00D8\u00FF', // JPEG
      '\u0089PNG', // PNG
    ];
    
    // Check for binary signatures
    for (const sig of binarySignatures) {
      if (content.startsWith(sig)) {
        return true;
      }
    }
    
    // Check for high concentration of non-printable characters
    const sample = content.substring(0, 1000);
    let nonPrintable = 0;
    
    for (let i = 0; i < sample.length; i++) {
      const code = sample.charCodeAt(i);
      if (code < 32 && ![9, 10, 13].includes(code)) { // Tab, LF, CR are ok
        nonPrintable++;
      }
    }
    
    // If more than 10% are non-printable, consider it binary
    return (nonPrintable / sample.length) > 0.1;
  };

  // Load document from URL
  const loadDocument = async (url: string) => {
    try {
      setLoading(true);
      setError(null);

      // Add cache-busting parameter
      const cacheBustUrl = `${url}${url.includes('?') ? '&' : '?'}t=${Date.now()}`;
      console.log('Loading document from:', cacheBustUrl);

      // Check if the URL is for a DOCX file
      const fileExtension = url.split('.').pop()?.toLowerCase();
      const isDocx = fileExtension === 'docx';
      
      try {
        if (isDocx) {
          // For DOCX files, use mammoth to convert to HTML
          const response = await fetch(cacheBustUrl);
          if (!response.ok) {
            throw new Error(`Failed to fetch document: ${response.status} ${response.statusText}`);
          }
          
          const arrayBuffer = await response.arrayBuffer();
          console.log('DOCX file loaded, converting to HTML...');
          
          try {
            const result = await mammoth.convertToHtml({ arrayBuffer });
            console.log('DOCX conversion successful');
            
            // Check if the result is binary or corrupted
            if (isBinaryContent(result.value)) {
              throw new Error('The document appears to be binary or corrupted');
            }
            
            setContent(result.value);
            if (editorRef.current) {
              editorRef.current.innerHTML = result.value;
            }
          } catch (conversionError) {
            console.error('Error converting DOCX to HTML:', conversionError);
            throw new Error(`Failed to convert DOCX: ${conversionError.message}`);
          }
        } else {
          // For HTML files, load directly
          const response = await fetch(cacheBustUrl);
          if (!response.ok) {
            throw new Error(`Failed to fetch document: ${response.status} ${response.statusText}`);
          }
          
          const text = await response.text();
          // Check if the response is binary/corrupted
          if (isBinaryContent(text)) {
            throw new Error('The document appears to be binary or corrupted');
          }
          
          setContent(text);
          if (editorRef.current) {
            editorRef.current.innerHTML = text;
          }
        }
      } catch (fetchError) {
        console.error('Error processing document:', fetchError);
        throw fetchError;
      }
    } catch (err) {
      console.error('Error loading document:', err);
      setError(`Failed to load document: ${err instanceof Error ? err.message : String(err)}`);
      
      // Clear any corrupted content
      setContent('');
      if (editorRef.current) {
        editorRef.current.innerHTML = '<p>Error loading document. Please try again.</p>';
      }
    } finally {
      setLoading(false);
    }
  };

  // Handle toolbar actions
  const handleToolbarAction = (command: string, value?: string) => {
    document.execCommand(command, false, value);
    // Focus the editor after toolbar action
    if (editorRef.current) {
      editorRef.current.focus();
      // Update content state
      setContent(editorRef.current.innerHTML);
    }
  };

  // Handle editor input
  const handleEditorInput = () => {
    if (editorRef.current) {
      setContent(editorRef.current.innerHTML);
    }
  };

  // Handle document save
  const handleSave = async () => {
    if (!onSave) return;
    
    try {
      setSaving(true);
      // Get the latest content from the editor
      const currentContent = editorRef.current?.innerHTML || content;
      await onSave(currentContent);
      console.log('Document saved successfully');
    } catch (err) {
      console.error('Error saving document:', err);
      setError(`Failed to save document: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSaving(false);
    }
  };

  // Handle refresh button click
  const handleRefresh = () => {
    if (documentUrl) {
      loadDocument(documentUrl);
    }
  };

  // Render loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center p-10">
        <Loader2 className="h-8 w-8 animate-spin mr-2" />
        <span>Loading document...</span>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <Card className="p-6 bg-red-50">
        <div className="text-center text-red-600">
          <h3 className="text-lg font-semibold mb-2">Error</h3>
          <p>{error}</p>
          {documentUrl && (
            <Button onClick={handleRefresh} className="mt-4">
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
          )}
        </div>
      </Card>
    );
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      <div className="flex-grow overflow-auto flex flex-col">
        {!readOnly && <SimpleToolbar onAction={handleToolbarAction} />}
        <div 
          ref={editorRef}
          className="flex-grow p-4 overflow-auto focus:outline-none"
          contentEditable={!readOnly}
          onInput={handleEditorInput}
          suppressContentEditableWarning={true}
          style={{
            minHeight: '200px',
            backgroundColor: '#fff',
            color: '#333',
            fontFamily: 'Arial, sans-serif',
            lineHeight: '1.5'
          }}
        />
      </div>
      
      {!readOnly && onSave && (
        <div className="flex justify-end gap-2 mt-4 p-2 border-t">
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Document
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
});

AdvancedDocEditor.displayName = 'AdvancedDocEditor';

export default AdvancedDocEditor; 