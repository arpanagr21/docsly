'use client';

import { useState, useCallback, useMemo, useEffect } from 'react';
import { CodeEditor } from '@/components/ui/code-editor';
import { componentService, type PreviewResponse } from '@/lib/api/services/components';
import type { Component, JSONSchema } from '@/types';

interface ComponentEditorProps {
  component?: Component;
  onSave: (data: {
    name: string;
    schema: JSONSchema;
    template: string;
    style_contract: Record<string, unknown>;
    default_styles: Record<string, unknown>;
  }) => void;
  isLoading?: boolean;
}

const DEFAULT_SCHEMA: JSONSchema = {
  type: 'object',
  properties: {
    title: { type: 'string', description: 'The title text' },
  },
  required: ['title'],
};

const DEFAULT_TEMPLATE = `## {{ title }}`;
const MARKDOWN_TAG_MAP = [
  { md: '# Heading', html: 'h1' },
  { md: '## Subheading', html: 'h2' },
  { md: 'Paragraph text', html: 'p' },
  { md: '- Bullet item', html: 'ul > li' },
  { md: '1. Ordered item', html: 'ol > li' },
  { md: '> Quote', html: 'blockquote' },
  { md: '`inline` / ```block```', html: 'code / pre > code' },
  { md: '| table | syntax |', html: 'table, thead, tbody, tr, th, td' },
  { md: '[Link](url)', html: 'a' },
  { md: '---', html: 'hr' },
];
const DEFAULT_STYLE_CONTRACT = {
  slots: ['root'],
  variants: ['default', 'compact', 'emphasis'],
};
const DEFAULT_STYLES = {
  base: {
    margin: '0.9rem 0',
    fontSize: '16px',
    lineHeight: '1.65',
  },
  slots: {
    root: {},
  },
  elements: {
    h1: { fontSize: '2rem', lineHeight: '1.2', margin: '0 0 0.7rem', fontWeight: '700' },
    h2: { fontSize: '1.5rem', lineHeight: '1.25', margin: '0 0 0.6rem', fontWeight: '700' },
    h3: { fontSize: '1.2rem', lineHeight: '1.3', margin: '0.7rem 0 0.45rem', fontWeight: '700' },
    p: { margin: '0.45rem 0', fontSize: '1rem' },
    li: { margin: '0.25rem 0', fontSize: '0.98rem' },
    table: { width: '100%', borderCollapse: 'collapse', margin: '0.7rem 0' },
    'th, td': { padding: '0.45rem 0.6rem', border: '1px solid #e5e7eb' },
    th: { background: '#f8fafc', fontWeight: '600' },
  },
  variants: {
    compact: {
      base: { margin: '0.45rem 0' },
    },
    emphasis: {
      base: { padding: '0.75rem 0.9rem', background: '#f8fafc', borderRadius: '0.5rem' },
    },
  },
};

export function ComponentEditor({ component, onSave, isLoading = false }: ComponentEditorProps) {
  const [name, setName] = useState(component?.name || '');
  const [schemaText, setSchemaText] = useState(
    component ? JSON.stringify(component.schema, null, 2) : JSON.stringify(DEFAULT_SCHEMA, null, 2)
  );
  const [template, setTemplate] = useState(component?.template || DEFAULT_TEMPLATE);
  const [styleContractText, setStyleContractText] = useState(
    JSON.stringify(component?.style_contract || DEFAULT_STYLE_CONTRACT, null, 2)
  );
  const [defaultStylesText, setDefaultStylesText] = useState(
    JSON.stringify(component?.default_styles || DEFAULT_STYLES, null, 2)
  );
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [styleContractError, setStyleContractError] = useState<string | null>(null);
  const [defaultStylesError, setDefaultStylesError] = useState<string | null>(null);
  const [previewHtml, setPreviewHtml] = useState('');
  const [previewMeta, setPreviewMeta] = useState<PreviewResponse['meta'] | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

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

  const parsedStyleContract = useMemo(() => {
    try {
      const parsed = JSON.parse(styleContractText);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        setStyleContractError('Style contract must be a JSON object');
        return null;
      }
      setStyleContractError(null);
      return parsed as Record<string, unknown>;
    } catch {
      setStyleContractError('Invalid JSON');
      return null;
    }
  }, [styleContractText]);

  const parsedDefaultStyles = useMemo(() => {
    try {
      const parsed = JSON.parse(defaultStylesText);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        setDefaultStylesError('Default styles must be a JSON object');
        return null;
      }
      setDefaultStylesError(null);
      return parsed as Record<string, unknown>;
    } catch {
      setDefaultStylesError('Invalid JSON');
      return null;
    }
  }, [defaultStylesText]);

  useEffect(() => {
    const timeout = setTimeout(async () => {
      setPreviewLoading(true);
      setPreviewError(null);
      try {
        const result = await componentService.previewTemplate(
          name || component?.name || 'preview-component',
          template,
          sampleProps,
          parsedStyleContract || {},
          parsedDefaultStyles || {}
        );
        setPreviewHtml(result.html || '');
        setPreviewMeta(result.meta || null);
      } catch (err) {
        setPreviewError(err instanceof Error ? err.message : 'Failed to render preview');
        setPreviewHtml('');
        setPreviewMeta(null);
      } finally {
        setPreviewLoading(false);
      }
    }, 250);

    return () => clearTimeout(timeout);
  }, [name, component?.name, template, sampleProps, parsedStyleContract, parsedDefaultStyles]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!parsedSchema) {
        return;
      }
      if (!parsedStyleContract || !parsedDefaultStyles) {
        return;
      }
      onSave({
        name,
        schema: parsedSchema,
        template,
        style_contract: parsedStyleContract,
        default_styles: parsedDefaultStyles,
      });
    },
    [name, parsedSchema, template, parsedStyleContract, parsedDefaultStyles, onSave]
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
          language="markdown"
          placeholder="## {{ title }}"
          readOnly={isReadOnly}
          minHeight="200px"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Style Contract (JSON)
        </label>
        {styleContractError && <p className="text-sm text-red-600 mb-1">{styleContractError}</p>}
        <CodeEditor
          value={styleContractText}
          onChange={setStyleContractText}
          language="json"
          placeholder='{"slots":["root"],"variants":["default"]}'
          readOnly={isReadOnly}
          minHeight="140px"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Default Styles (JSON)
        </label>
        {defaultStylesError && <p className="text-sm text-red-600 mb-1">{defaultStylesError}</p>}
        <CodeEditor
          value={defaultStylesText}
          onChange={setDefaultStylesText}
          language="json"
          placeholder='{"base":{"margin":"1rem 0"}}'
          readOnly={isReadOnly}
          minHeight="180px"
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
          {previewLoading && <div className="text-xs text-gray-500">Rendering preview...</div>}
          {previewError && <div className="text-sm text-red-600">{previewError}</div>}
          {!previewLoading && !previewError && (
            <div
              className="preview-content docsly-preview component-preview border-t pt-3"
              dangerouslySetInnerHTML={{ __html: previewHtml }}
            />
          )}
        </div>
      </div>

      <div className="rounded-md border border-gray-200 bg-gray-50 p-4">
        <h3 className="text-sm font-semibold text-gray-800 mb-2">How Styling Maps</h3>
        <p className="text-xs text-gray-600 mb-3">
          Use <code>elements</code> in default styles to target rendered tags.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
          {MARKDOWN_TAG_MAP.map((entry) => (
            <div key={entry.md} className="rounded border border-gray-200 bg-white px-2 py-1.5">
              <span className="font-mono text-gray-700">{entry.md}</span>
              <span className="mx-1 text-gray-400">→</span>
              <span className="font-mono text-blue-700">{entry.html}</span>
            </div>
          ))}
        </div>
        <div className="mt-3">
          <p className="text-xs text-gray-600 mb-1">Detected in current preview:</p>
          {(previewMeta?.rendered_tags || []).length === 0 ? (
            <p className="text-xs text-gray-500">No rendered tags yet.</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {(previewMeta?.rendered_tags || []).map((tag) => (
                <span key={tag} className="inline-flex rounded bg-blue-100 text-blue-800 px-2 py-0.5 text-xs font-mono">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="rounded border border-gray-200 bg-white p-2">
            <p className="font-semibold text-gray-700 mb-1">Markdown Block Outline</p>
            {(previewMeta?.markdown_outline || []).length === 0 ? (
              <p className="text-gray-500">No blocks detected.</p>
            ) : (
              <div className="space-y-1">
                {(previewMeta?.markdown_outline || []).map((node, idx) => (
                  <div key={`${node.type}-${idx}`} className="font-mono text-[11px] text-gray-700">
                    {`${' '.repeat(Math.max(0, node.level) * 2)}${node.type} <${node.tag}>`}
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="rounded border border-gray-200 bg-white p-2">
            <p className="font-semibold text-gray-700 mb-1">Template Diagnostics</p>
            <div className="space-y-1">
              <div>
                <span className="text-gray-500">Placeholders:</span>{' '}
                <span className="font-mono">{(previewMeta?.placeholders || []).join(', ') || 'none'}</span>
              </div>
              <div>
                <span className="text-gray-500">Unresolved:</span>{' '}
                <span className="font-mono text-red-700">
                  {(previewMeta?.unresolved_placeholders || []).join(', ') || 'none'}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Slot Contract Mismatch:</span>{' '}
                <span className="font-mono">
                  {[
                    ...(previewMeta?.undeclared_slots || []).map((s) => `missing:${s}`),
                    ...(previewMeta?.extra_slots || []).map((s) => `extra:${s}`),
                  ].join(', ') || 'none'}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Variant Contract Mismatch:</span>{' '}
                <span className="font-mono">
                  {[
                    ...(previewMeta?.undeclared_variants || []).map((s) => `missing:${s}`),
                    ...(previewMeta?.extra_variants || []).map((s) => `extra:${s}`),
                  ].join(', ') || 'none'}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="rounded border border-gray-200 bg-white p-2">
            <p className="font-semibold text-gray-700 mb-1">Interpolated Markdown</p>
            <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-[11px] text-gray-700">
              {(previewMeta?.interpolated_markdown || '').trim() || 'No markdown output yet.'}
            </pre>
          </div>
          <div className="rounded border border-gray-200 bg-white p-2">
            <p className="font-semibold text-gray-700 mb-1">Element Style Coverage</p>
            <div className="space-y-1">
              <div>
                <span className="text-gray-500">Defined selectors:</span>{' '}
                <span className="font-mono">
                  {(previewMeta?.element_selectors || []).join(', ') || 'none'}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Styled rendered tags:</span>{' '}
                <span className="font-mono text-green-700">
                  {(previewMeta?.styled_rendered_tags || []).join(', ') || 'none'}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Unstyled rendered tags:</span>{' '}
                <span className="font-mono text-amber-700">
                  {(previewMeta?.unstyled_rendered_tags || []).join(', ') || 'none'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Submit Button */}
      {!isReadOnly && (
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isLoading || !parsedSchema || !parsedStyleContract || !parsedDefaultStyles || !name.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Saving...' : component ? 'Update Component' : 'Create Component'}
          </button>
        </div>
      )}
    </form>
  );
}
