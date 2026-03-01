'use client';

import { useState, useCallback, useMemo } from 'react';
import { CodeEditor } from '@/components/ui/code-editor';
import type { Component, JSONSchema } from '@/types';

interface ComponentEditorProps {
  component?: Component;
  onSave: (data: { name: string; schema: JSONSchema; template: string }) => void;
  isLoading?: boolean;
}

const DEFAULT_SCHEMA: JSONSchema = {
  type: 'object',
  properties: {
    title: { type: 'string', description: 'The title text' },
  },
  required: ['title'],
};

const DEFAULT_TEMPLATE = `<div class="component">
  <h1>{{ title }}</h1>
</div>`;

export function ComponentEditor({ component, onSave, isLoading = false }: ComponentEditorProps) {
  const [name, setName] = useState(component?.name || '');
  const [schemaText, setSchemaText] = useState(
    component ? JSON.stringify(component.schema, null, 2) : JSON.stringify(DEFAULT_SCHEMA, null, 2)
  );
  const [template, setTemplate] = useState(component?.template || DEFAULT_TEMPLATE);
  const [schemaError, setSchemaError] = useState<string | null>(null);

  const parsedSchema = useMemo(() => {
    try {
      const parsed = JSON.parse(schemaText);
      setSchemaError(null);
      return parsed as JSONSchema;
    } catch (e) {
      setSchemaError('Invalid JSON');
      return null;
    }
  }, [schemaText]);

  const sampleProps = useMemo(() => {
    if (!parsedSchema?.properties) return {};

    const props: Record<string, any> = {};
    for (const [key, value] of Object.entries(parsedSchema.properties)) {
      switch (value.type) {
        case 'string':
          props[key] = value.default || `Sample ${key}`;
          break;
        case 'number':
          props[key] = value.default || 42;
          break;
        case 'boolean':
          props[key] = value.default ?? true;
          break;
        case 'array':
          props[key] = value.default || [];
          break;
        case 'object':
          props[key] = value.default || {};
          break;
        default:
          props[key] = value.default || `Sample ${key}`;
      }
    }
    return props;
  }, [parsedSchema]);

  const previewHtml = useMemo(() => {
    // Simple {{prop}} placeholder interpolation for preview
    let html = template;
    for (const [key, value] of Object.entries(sampleProps)) {
      const regex = new RegExp(`\\{\\{\\s*${key}\\s*\\}\\}`, 'g');
      html = html.replace(regex, String(value));
    }
    return html;
  }, [template, sampleProps]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!parsedSchema) {
        return;
      }
      onSave({ name, schema: parsedSchema, template });
    },
    [name, parsedSchema, template, onSave]
  );

  const isReadOnly = component?.is_builtin || false;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Name Input */}
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
          Component Name
        </label>
        <input
          type="text"
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isReadOnly}
          required
          placeholder="e.g., heading, paragraph, image"
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
        />
      </div>

      {/* Schema Editor */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Schema (JSON)
        </label>
        {schemaError && (
          <p className="text-sm text-red-600 mb-1">{schemaError}</p>
        )}
        <CodeEditor
          value={schemaText}
          onChange={setSchemaText}
          language="json"
          placeholder='{"type": "object", "properties": {...}}'
          readOnly={isReadOnly}
          minHeight="150px"
        />
      </div>

      {/* Template Editor */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Template (Markdown + <code>{'{{prop}}'}</code> placeholders)
        </label>
        <CodeEditor
          value={template}
          onChange={setTemplate}
          language="html"
          placeholder="<div>{{ title }}</div>"
          readOnly={isReadOnly}
          minHeight="200px"
        />
      </div>

      {/* Preview Section */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Preview
        </label>
        <div className="border border-gray-300 rounded-md p-4 bg-white min-h-[100px]">
          <div className="text-xs text-gray-500 mb-2">
            Sample props: {JSON.stringify(sampleProps)}
          </div>
          <div
            className="preview-content border-t pt-2"
            dangerouslySetInnerHTML={{ __html: previewHtml }}
          />
        </div>
      </div>

      {/* Submit Button */}
      {!isReadOnly && (
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isLoading || !parsedSchema || !name.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Saving...' : component ? 'Update Component' : 'Create Component'}
          </button>
        </div>
      )}
    </form>
  );
}
