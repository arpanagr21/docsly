'use client';

import { useState, useCallback, useMemo } from 'react';
import type { Theme, ThemeVariables } from '@/types';

interface ThemeEditorProps {
  theme?: Theme;
  onSave: (data: { name: string; variables: ThemeVariables; is_default: boolean }) => void;
  isLoading?: boolean;
}

interface VariableConfig {
  key: string;
  label: string;
  type: 'color' | 'text' | 'number';
  defaultValue: string;
  unit?: string;
}

const VARIABLE_CONFIGS: VariableConfig[] = [
  { key: 'font-family', label: 'Font Family', type: 'text', defaultValue: 'system-ui, sans-serif' },
  { key: 'text-color', label: 'Text Color', type: 'color', defaultValue: '#1f2937' },
  { key: 'background-color', label: 'Background Color', type: 'color', defaultValue: '#ffffff' },
  { key: 'primary-color', label: 'Primary Color', type: 'color', defaultValue: '#3b82f6' },
  { key: 'line-height', label: 'Line Height', type: 'number', defaultValue: '1.6' },
  { key: 'max-width', label: 'Max Width', type: 'text', defaultValue: '800px' },
];

const DEFAULT_VARIABLES: ThemeVariables = VARIABLE_CONFIGS.reduce(
  (acc, config) => ({ ...acc, [config.key]: config.defaultValue }),
  {} as ThemeVariables
);
const ELEMENT_STYLES_KEY = '__element_styles';
const DEFAULT_ELEMENT_STYLES = {
  h1: { fontSize: '2rem', fontWeight: '700', marginBottom: '0.75rem' },
  h2: { fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.6rem' },
  p: { marginBottom: '0.75rem' },
  table: { width: '100%', borderCollapse: 'collapse' },
  'table th': { background: '#f8fafc', fontWeight: '600' },
  'table th, table td': { border: '1px solid #e5e7eb', padding: '0.5rem 0.75rem' },
  '.dsl-row': { gap: '1rem', margin: '1rem 0' },
  '.dsl-column': { minHeight: '1px' },
};
const COMPONENT_STYLES_KEY = '__component_styles';
const DEFAULT_COMPONENT_STYLES = {
  heading: {
    base: { margin: '1rem 0' },
    slots: { root: { color: '#0f172a' } },
  },
  'pricing-table': {
    base: { margin: '1rem 0' },
    slots: { root: { border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '0.75rem' } },
  },
};

function getElementStyles(variables: ThemeVariables): Record<string, unknown> {
  const value = variables[ELEMENT_STYLES_KEY];
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return DEFAULT_ELEMENT_STYLES;
}

function getComponentStyles(variables: ThemeVariables): Record<string, unknown> {
  const value = variables[COMPONENT_STYLES_KEY];
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return DEFAULT_COMPONENT_STYLES;
}

export function ThemeEditor({ theme, onSave, isLoading = false }: ThemeEditorProps) {
  const [name, setName] = useState(theme?.name || '');
  const [variables, setVariables] = useState<ThemeVariables>(
    theme?.variables || DEFAULT_VARIABLES
  );
  const [elementStylesText, setElementStylesText] = useState(
    JSON.stringify(getElementStyles(theme?.variables || DEFAULT_VARIABLES), null, 2)
  );
  const [componentStylesText, setComponentStylesText] = useState(
    JSON.stringify(getComponentStyles(theme?.variables || DEFAULT_VARIABLES), null, 2)
  );
  const [elementStylesError, setElementStylesError] = useState<string | null>(null);
  const [componentStylesError, setComponentStylesError] = useState<string | null>(null);
  const [isDefault, setIsDefault] = useState(theme?.is_default || false);

  const updateVariable = useCallback((key: string, value: string) => {
    setVariables((prev) => ({ ...prev, [key]: value }));
  }, []);
  const getVariableValue = useCallback((key: string, fallback: string) => {
    const value = variables[key];
    if (typeof value === 'string' || typeof value === 'number') {
      return String(value);
    }
    return fallback;
  }, [variables]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      try {
        const parsedStyles = JSON.parse(elementStylesText);
        const parsedComponentStyles = JSON.parse(componentStylesText);
        setElementStylesError(null);
        setComponentStylesError(null);
        onSave({
          name,
          variables: {
            ...variables,
            [ELEMENT_STYLES_KEY]: parsedStyles,
            [COMPONENT_STYLES_KEY]: parsedComponentStyles,
          },
          is_default: isDefault,
        });
      } catch {
        try {
          JSON.parse(elementStylesText);
          setElementStylesError(null);
        } catch {
          setElementStylesError('Element styles must be valid JSON');
        }
        try {
          JSON.parse(componentStylesText);
          setComponentStylesError(null);
        } catch {
          setComponentStylesError('Component styles must be valid JSON');
        }
      }
    },
    [name, variables, elementStylesText, componentStylesText, isDefault, onSave]
  );

  const isReadOnly = theme?.is_builtin || false;

  const previewStyles = useMemo((): React.CSSProperties => {
    return {
      fontFamily: String(variables['font-family'] || DEFAULT_VARIABLES['font-family']),
      color: String(variables['text-color'] || DEFAULT_VARIABLES['text-color']),
      backgroundColor: String(variables['background-color'] || DEFAULT_VARIABLES['background-color']),
      lineHeight: String(variables['line-height'] || DEFAULT_VARIABLES['line-height']),
      maxWidth: String(variables['max-width'] || DEFAULT_VARIABLES['max-width']),
    };
  }, [variables]);

  const primaryColor = String(variables['primary-color'] || DEFAULT_VARIABLES['primary-color']);

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Name Input */}
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
          Theme Name
        </label>
        <input
          type="text"
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isReadOnly}
          required
          placeholder="e.g., Light, Dark, Professional"
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
        />
      </div>

      {/* Variable Editors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {VARIABLE_CONFIGS.map((config) => (
          <div key={config.key}>
            <label
              htmlFor={config.key}
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              {config.label}
            </label>
            {config.type === 'color' ? (
              <div className="flex gap-2">
                <input
                  type="color"
                  id={config.key}
                  value={getVariableValue(config.key, config.defaultValue)}
                  onChange={(e) => updateVariable(config.key, e.target.value)}
                  disabled={isReadOnly}
                  className="h-10 w-14 p-1 border border-gray-300 rounded cursor-pointer disabled:cursor-not-allowed"
                />
                <input
                  type="text"
                  value={getVariableValue(config.key, config.defaultValue)}
                  onChange={(e) => updateVariable(config.key, e.target.value)}
                  disabled={isReadOnly}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 font-mono text-sm"
                />
              </div>
            ) : config.type === 'number' ? (
              <input
                type="number"
                id={config.key}
                value={getVariableValue(config.key, config.defaultValue)}
                onChange={(e) => updateVariable(config.key, e.target.value)}
                disabled={isReadOnly}
                step="0.1"
                min="0"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              />
            ) : (
              <input
                type="text"
                id={config.key}
                value={getVariableValue(config.key, config.defaultValue)}
                onChange={(e) => updateVariable(config.key, e.target.value)}
                disabled={isReadOnly}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              />
            )}
          </div>
        ))}
      </div>

      <div>
        <label htmlFor="element-styles" className="block text-sm font-medium text-gray-700 mb-1">
          Element Styles (centralized)
        </label>
        <p className="text-xs text-gray-500 mb-2">
          Configure per-element CSS rules used by all markdown docs on this theme.
        </p>
        {elementStylesError && (
          <p className="text-sm text-red-600 mb-2">{elementStylesError}</p>
        )}
        <textarea
          id="element-styles"
          value={elementStylesText}
          onChange={(e) => setElementStylesText(e.target.value)}
          disabled={isReadOnly}
          className="w-full min-h-[220px] px-3 py-2 border border-gray-300 rounded-md shadow-sm font-mono text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
        />
      </div>

      <div>
        <label htmlFor="component-styles" className="block text-sm font-medium text-gray-700 mb-1">
          Component Style Overrides (centralized)
        </label>
        <p className="text-xs text-gray-500 mb-2">
          Override component base/slot styles by component name.
        </p>
        {componentStylesError && (
          <p className="text-sm text-red-600 mb-2">{componentStylesError}</p>
        )}
        <textarea
          id="component-styles"
          value={componentStylesText}
          onChange={(e) => setComponentStylesText(e.target.value)}
          disabled={isReadOnly}
          className="w-full min-h-[220px] px-3 py-2 border border-gray-300 rounded-md shadow-sm font-mono text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
        />
      </div>

      {/* Set as Default Checkbox */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_default"
          checked={isDefault}
          onChange={(e) => setIsDefault(e.target.checked)}
          disabled={isReadOnly}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:cursor-not-allowed"
        />
        <label htmlFor="is_default" className="text-sm text-gray-700">
          Set as default theme
        </label>
      </div>

      {/* Live Preview */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Preview
        </label>
        <div
          className="border border-gray-300 rounded-md p-6"
          style={previewStyles}
        >
          <h1 className="text-2xl font-bold mb-4" style={{ color: primaryColor }}>
            Sample Heading
          </h1>
          <p className="mb-4">
            This is a sample paragraph showing how your theme will look. The text
            color, background color, font family, and line height are all applied
            from your theme variables.
          </p>
          <a href="#" style={{ color: primaryColor }} className="underline">
            Sample Link
          </a>
        </div>
      </div>

      {/* Submit Button */}
      {!isReadOnly && (
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isLoading || !name.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Saving...' : theme ? 'Update Theme' : 'Create Theme'}
          </button>
        </div>
      )}
    </form>
  );
}
