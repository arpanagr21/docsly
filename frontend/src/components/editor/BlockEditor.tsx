'use client';

import React, { useState } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Trash2, ChevronUp, ChevronDown, Type, Box, Eye, EyeOff } from 'lucide-react';
import { ComponentPicker } from './ComponentPicker';
import { SchemaPropsEditor } from './SchemaPropsEditor';
import { BlockPreview } from './BlockPreview';
import { useComponentByName } from '@/hooks/useComponents';
import type { Block } from '@/types/document';
import type { Component } from '@/types';

export interface BlockEditorProps {
  block: Block;
  onChange: (block: Block) => void;
  onDelete: () => void;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  canMoveUp?: boolean;
  canMoveDown?: boolean;
}

export function BlockEditor({
  block,
  onChange,
  onDelete,
  onMoveUp,
  onMoveDown,
  canMoveUp = true,
  canMoveDown = true,
}: BlockEditorProps) {
  const [showPreview, setShowPreview] = useState(true);
  // Fetch component schema when a component is selected
  const { data: selectedComponent } = useComponentByName(block.name || '');

  const handleTypeChange = (newType: 'markdown' | 'component') => {
    if (newType === 'markdown') {
      onChange({
        type: 'markdown',
        content: '',
      });
    } else {
      onChange({
        type: 'component',
        name: '',
        props: {},
      });
    }
  };

  const handleMarkdownChange = (content: string) => {
    onChange({
      ...block,
      content,
    });
  };

  const handleComponentSelect = (component: Component) => {
    // Initialize props with defaults from schema
    const defaultProps: Record<string, unknown> = {};
    const properties = component.schema?.properties || {};

    for (const [key, prop] of Object.entries(properties)) {
      const property = prop as { default?: unknown; type: string };
      if (property.default !== undefined) {
        defaultProps[key] = property.default;
      }
    }

    onChange({
      ...block,
      name: component.name,
      props: defaultProps,
    });
  };

  const handlePropsChange = (props: Record<string, unknown>) => {
    onChange({
      ...block,
      props,
    });
  };

  return (
    <div className="border border-gray-200 rounded-lg bg-white shadow-sm">
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 bg-gray-50 rounded-t-lg">
        <div className="flex items-center gap-2">
          <select
            value={block.type}
            onChange={(e) => handleTypeChange(e.target.value as 'markdown' | 'component')}
            className="text-sm border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="markdown">Markdown</option>
            <option value="component">Component</option>
          </select>
          {block.type === 'markdown' ? (
            <Type className="w-4 h-4 text-gray-500" />
          ) : (
            <Box className="w-4 h-4 text-gray-500" />
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowPreview(!showPreview)}
            className={`p-1 transition-colors ${showPreview ? 'text-blue-500 hover:text-blue-700' : 'text-gray-400 hover:text-gray-600'}`}
            title={showPreview ? 'Hide preview' : 'Show preview'}
          >
            {showPreview ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          </button>
          <div className="w-px h-4 bg-gray-200 mx-1" />
          <button
            onClick={onMoveUp}
            disabled={!canMoveUp}
            className="p-1 text-gray-500 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Move up"
          >
            <ChevronUp className="w-4 h-4" />
          </button>
          <button
            onClick={onMoveDown}
            disabled={!canMoveDown}
            className="p-1 text-gray-500 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Move down"
          >
            <ChevronDown className="w-4 h-4" />
          </button>
          <button
            onClick={onDelete}
            className="p-1 text-red-500 hover:text-red-700"
            title="Delete block"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="p-3">
        {block.type === 'markdown' ? (
          <Textarea
            value={block.content || ''}
            onChange={(e) => handleMarkdownChange(e.target.value)}
            placeholder="Enter markdown content..."
            className="min-h-[120px] font-mono text-sm"
          />
        ) : (
          <div className="space-y-4">
            {/* Component Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Component
              </label>
              <ComponentPicker
                selectedComponent={block.name}
                onSelect={handleComponentSelect}
              />
            </div>

            {/* Props Editor - show only when component is selected */}
            {block.name && selectedComponent && (
              <div className="border-t pt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Configure Properties
                </label>
                <SchemaPropsEditor
                  schema={selectedComponent.schema}
                  props={(block.props || {}) as Record<string, unknown>}
                  onChange={handlePropsChange}
                />
              </div>
            )}

            {block.name && !selectedComponent && (
              <div className="text-sm text-gray-500 italic">
                Loading component schema...
              </div>
            )}
          </div>
        )}
      </div>

      {/* Live Preview Section */}
      {showPreview && (
        <div className="border-t border-gray-200 p-3 bg-gray-50/50">
          <BlockPreview block={block} />
        </div>
      )}
    </div>
  );
}
