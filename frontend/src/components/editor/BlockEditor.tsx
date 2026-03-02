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

const CORE_COMPONENT_MAP: Record<string, Component> = {
  row: {
    id: -1,
    user_id: null,
    name: 'row',
    version: '1',
    schema: {
      type: 'object',
      properties: {
        columns: { type: 'number', default: 2 },
        gap: { type: 'string', default: '1rem' },
        class: { type: 'string' },
        style: { type: 'string' },
      },
    },
    template: '',
    is_active: true,
    is_builtin: true,
  },
  column: {
    id: -2,
    user_id: null,
    name: 'column',
    version: '1',
    schema: {
      type: 'object',
      properties: {
        span: { type: 'number', default: 6 },
        class: { type: 'string' },
        style: { type: 'string' },
      },
    },
    template: '',
    is_active: true,
    is_builtin: true,
  },
  table: {
    id: -3,
    user_id: null,
    name: 'table',
    version: '1',
    schema: {
      type: 'object',
      properties: {
        headers: { type: 'array', default: ['Column A', 'Column B'] },
        rows: { type: 'array', default: [['Value 1', 'Value 2']] },
        class: { type: 'string' },
        style: { type: 'string' },
      },
    },
    template: '',
    is_active: true,
    is_builtin: true,
  },
};

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
  const isCoreBlock = ['row', 'column', 'table'].includes((block.name || '').toLowerCase());
  const coreComponent = block.name ? CORE_COMPONENT_MAP[block.name.toLowerCase()] : undefined;
  // Fetch component schema when a component is selected
  const { data: selectedComponent, isLoading: isComponentLoading } = useComponentByName(
    isCoreBlock ? '' : (block.name || '')
  );
  const effectiveComponent = selectedComponent || coreComponent;

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
      version: Number(component.version || 1),
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
            type="button"
            onClick={() => setShowPreview(!showPreview)}
            className={`p-1 transition-colors ${showPreview ? 'text-blue-500 hover:text-blue-700' : 'text-gray-400 hover:text-gray-600'}`}
            title={showPreview ? 'Hide preview' : 'Show preview'}
          >
            {showPreview ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          </button>
          <div className="w-px h-4 bg-gray-200 mx-1" />
          <button
            type="button"
            onClick={onMoveUp}
            disabled={!canMoveUp}
            className="p-1 text-gray-500 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Move up"
          >
            <ChevronUp className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={onMoveDown}
            disabled={!canMoveDown}
            className="p-1 text-gray-500 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Move down"
          >
            <ChevronDown className="w-4 h-4" />
          </button>
          <button
            type="button"
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
            {block.name && effectiveComponent && (
              <div className="border-t pt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Configure Properties
                </label>
                <SchemaPropsEditor
                  schema={effectiveComponent.schema}
                  props={(block.props || {}) as Record<string, unknown>}
                  onChange={handlePropsChange}
                />
                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-600">
                      Version
                    </label>
                    <input
                      type="number"
                      min={1}
                      value={block.version || ''}
                      onChange={(e) =>
                        onChange({
                          ...block,
                          version: e.target.value ? Number(e.target.value) : undefined,
                        })
                      }
                      className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
                      placeholder="Latest"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-600">
                      Slot Markdown (optional)
                    </label>
                    <Textarea
                      value={block.inner_markdown || ''}
                      onChange={(e) =>
                        onChange({
                          ...block,
                          inner_markdown: e.target.value,
                        })
                      }
                      className="min-h-[76px] font-mono text-xs"
                      placeholder="Inner markdown content passed into component slot"
                    />
                  </div>
                </div>
              </div>
            )}

            {block.name && isComponentLoading && !isCoreBlock && (
              <div className="text-sm text-gray-500 italic">
                Loading component schema...
              </div>
            )}
            {block.name && !effectiveComponent && !isComponentLoading && !isCoreBlock && (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
                Component schema not found. Switch to Raw Markdown mode if you need full manual control for this block.
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
