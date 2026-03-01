'use client';

import { useCallback, useRef, useEffect, useState } from 'react';

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: string;
  placeholder?: string;
  readOnly?: boolean;
  minHeight?: string;
  className?: string;
}

export function CodeEditor({
  value,
  onChange,
  language = 'plaintext',
  placeholder = '',
  readOnly = false,
  minHeight = '200px',
  className = '',
}: CodeEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lineNumbersRef = useRef<HTMLDivElement>(null);
  const [lineCount, setLineCount] = useState(1);

  const updateLineNumbers = useCallback(() => {
    const lines = value.split('\n').length;
    setLineCount(lines);
  }, [value]);

  useEffect(() => {
    updateLineNumbers();
  }, [updateLineNumbers]);

  const handleScroll = useCallback(() => {
    if (textareaRef.current && lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Tab') {
        e.preventDefault();
        const textarea = textareaRef.current;
        if (!textarea) return;

        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const newValue = value.substring(0, start) + '  ' + value.substring(end);
        onChange(newValue);

        // Set cursor position after tab
        requestAnimationFrame(() => {
          textarea.selectionStart = textarea.selectionEnd = start + 2;
        });
      }
    },
    [value, onChange]
  );

  const lineNumbers = Array.from({ length: lineCount }, (_, i) => i + 1);

  return (
    <div
      className={`relative flex border border-gray-300 rounded-md bg-gray-50 overflow-hidden ${className}`}
      style={{ minHeight }}
    >
      {/* Line numbers */}
      <div
        ref={lineNumbersRef}
        className="flex-shrink-0 w-12 bg-gray-100 border-r border-gray-300 overflow-hidden select-none"
        aria-hidden="true"
      >
        <div className="py-2 text-right pr-2">
          {lineNumbers.map((num) => (
            <div
              key={num}
              className="text-xs text-gray-400 leading-5 font-mono"
            >
              {num}
            </div>
          ))}
        </div>
      </div>

      {/* Code textarea */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onScroll={handleScroll}
        onKeyDown={handleKeyDown}
        readOnly={readOnly}
        placeholder={placeholder}
        spellCheck={false}
        className="flex-1 p-2 font-mono text-sm leading-5 bg-transparent resize-none outline-none"
        style={{ minHeight }}
        data-language={language}
      />
    </div>
  );
}
