'use client';

import React, { useEffect, useState, useRef } from 'react';
import { Eye, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { componentService } from '@/lib/api/services/components';
import type { Block } from '@/types/document';

export interface BlockPreviewProps {
  block: Block;
  minimal?: boolean;
  maxHeight?: string;
}

export function BlockPreview({ block, minimal = false, maxHeight = '400px' }: BlockPreviewProps) {
  const [html, setHtml] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const fetchPreview = async () => {
    // Don't fetch if block is incomplete
    if (block.type === 'component' && !block.name) {
      setHtml(null);
      return;
    }
    if (block.type === 'markdown' && !block.content?.trim()) {
      setHtml(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await componentService.previewBlock(block);
      setHtml(response.html);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load preview');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Debounce preview fetching
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      fetchPreview();
    }, 500);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [block.type, block.name, block.version, block.content, block.inner_markdown, JSON.stringify(block.props)]);

  // Empty state
  if (!html && !isLoading && !error) {
    const message = block.type === 'component'
      ? 'Select a component to see preview'
      : 'Enter content to see preview';

    return (
      <div className="flex items-center justify-center py-8 bg-gray-50 rounded-lg border border-dashed border-gray-200">
        <div className="text-center text-gray-400">
          <Eye className="w-6 h-6 mx-auto mb-2 opacity-50" />
          <p className="text-sm">{message}</p>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    if (minimal) {
      return (
        <div className="flex items-center justify-center py-6 bg-white rounded-lg border border-gray-200">
          <Loader2 className="w-4 h-4 animate-spin text-blue-500 mr-2" />
          <span className="text-xs text-gray-500">Rendering...</span>
        </div>
      );
    }
    return (
      <div className="flex items-center justify-center py-8 bg-gray-50 rounded-lg border border-gray-200">
        <Loader2 className="w-5 h-5 animate-spin text-blue-500 mr-2" />
        <span className="text-sm text-gray-500">Rendering preview...</span>
      </div>
    );
  }

  // Error state
  if (error) {
    if (minimal) {
      return (
        <div className="py-3 px-3 bg-red-50 rounded-lg border border-red-200 text-red-700 text-xs">
          {error}
        </div>
      );
    }
    return (
      <div className="flex items-center justify-between py-4 px-4 bg-red-50 rounded-lg border border-red-200">
        <div className="flex items-center gap-2 text-red-600">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">{error}</span>
        </div>
        <button
          onClick={fetchPreview}
          className="p-1.5 text-red-500 hover:text-red-700 hover:bg-red-100 rounded transition-colors"
          title="Retry"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
    );
  }

  // Preview content
  if (minimal) {
    return (
      <div
        className="preview-content docsly-preview bg-white border border-gray-200 rounded-lg p-4 overflow-auto"
        style={{ maxHeight }}
        dangerouslySetInnerHTML={{ __html: html || '' }}
      />
    );
  }

  return (
    <div className="relative">
      {/* Preview header */}
      <div className="flex items-center justify-between px-3 py-2 bg-gradient-to-r from-gray-50 to-gray-100 border border-gray-200 rounded-t-lg">
        <div className="flex items-center gap-2">
          <Eye className="w-4 h-4 text-gray-400" />
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Preview</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
          </span>
          <span className="text-xs text-green-600">Live</span>
        </div>
      </div>

      {/* Rendered content */}
      <div
        className="preview-content docsly-preview bg-white border border-t-0 border-gray-200 rounded-b-lg p-4 overflow-auto"
        style={{ maxHeight }}
        dangerouslySetInnerHTML={{ __html: html || '' }}
      />
    </div>
  );
}
