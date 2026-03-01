'use client';

import React, { useMemo, useState } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { useComponents } from '@/hooks/useComponents';
import type { JSONSchema } from '@/types';
import type { DocumentContent } from '@/types/document';

export interface DocumentEditorProps {
  content: DocumentContent;
  onChange: (content: DocumentContent) => void;
}

export function DocumentEditor({ content, onChange }: DocumentEditorProps) {
  const { data: components = [] } = useComponents();
  const [selectedComponent, setSelectedComponent] = useState('');

  const handleMarkdownChange = (markdown: string) => {
    onChange({
      ...content,
      markdown,
    });
  };

  const activeComponents = useMemo(
    () => components.filter((component) => component.is_active),
    [components]
  );

  const buildComponentSnippet = () => {
    if (!selectedComponent) {
      return '{{< component-name >}}';
    }

    const component = activeComponents.find((entry) => entry.name === selectedComponent);
    if (!component) {
      return `{{< ${selectedComponent} >}}`;
    }

    const schema = component.schema as JSONSchema;
    const props: Record<string, unknown> = {};
    const required = new Set(schema.required || []);
    const properties = schema.properties || {};

    Object.entries(properties).forEach(([key, config]) => {
      if (config.default !== undefined) {
        props[key] = config.default;
      } else if (required.has(key)) {
        if (config.type === 'string') props[key] = `your-${key}`;
        else if (config.type === 'number') props[key] = 0;
        else if (config.type === 'boolean') props[key] = false;
      }
    });

    if (Object.keys(props).length === 0) {
      return `{{< ${selectedComponent} >}}`;
    }

    const payload = JSON.stringify(props).replace(/'/g, "\\'");
    return `{{< ${selectedComponent} props_json='${payload}' >}}`;
  };

  const insertSnippet = (snippet: string) => {
    const next = (content.markdown || '').trim();
    onChange({
      ...content,
      markdown: next ? `${next}\n\n${snippet}` : snippet,
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => insertSnippet('{{< row columns=2 gap="1rem" >}}\n{{< column span=6 >}}\nColumn A\n{{< /column >}}\n{{< column span=6 >}}\nColumn B\n{{< /column >}}\n{{< /row >}}')}
          className="px-3 py-1.5 text-xs border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Insert Row/Column
        </button>
        <button
          type="button"
          onClick={() => insertSnippet('{{< table headers="Name|Plan|Price" rows="Acme|Pro|49;Beta|Starter|19" >}}')}
          className="px-3 py-1.5 text-xs border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Insert Table
        </button>
        <button
          type="button"
          onClick={() => insertSnippet(buildComponentSnippet())}
          className="px-3 py-1.5 text-xs border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Insert Custom Element
        </button>
        <select
          value={selectedComponent}
          onChange={(e) => setSelectedComponent(e.target.value)}
          className="px-2 py-1.5 text-xs border border-gray-300 rounded-md bg-white"
        >
          <option value="">component-name</option>
          {activeComponents.map((component) => (
            <option key={component.id} value={component.name}>
              {component.name}
            </option>
          ))}
        </select>
      </div>

      <Textarea
        value={content.markdown || ''}
        onChange={(e) => handleMarkdownChange(e.target.value)}
        placeholder="Write markdown here. Use shortcodes for custom elements, e.g. {{< row >}} ... {{< /row >}}."
        className="min-h-[500px] font-mono text-sm leading-6"
      />

      <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
        Theme-level element styles are configured under theme variables key: <code>__element_styles</code>.
      </div>
    </div>
  );
}
