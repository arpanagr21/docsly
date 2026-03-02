'use client';

import React, { useMemo, useRef } from 'react';
import {
  Heading1,
  Heading2,
  Bold,
  Italic,
  List,
  ListOrdered,
  Link2,
  Quote,
  Code,
  Minus,
  Layout,
  Table,
  FileText,
} from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import type { DocumentContent } from '@/types/document';

export interface DocumentEditorProps {
  content: DocumentContent;
  onChange: (content: DocumentContent) => void;
}

type ToolbarAction = {
  id: string;
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
};

const TABLE_SNIPPET = `| Item | Description | Price |
| --- | --- | --- |
| Starter | Basic package | $500 |
| Pro | Premium package | $1200 |`;

const ROW_LAYOUT_SNIPPET = `:::row columns=2 gap="1rem"
:::column span=6
## Left Column
Add your content here.
:::

:::column span=6
## Right Column
Add your content here.
:::
:::`;

const PROPOSAL_SKELETON = `# Proposal Title

## Executive Summary
Write a concise summary of the proposal.

## Scope of Work
${TABLE_SNIPPET}

## Timeline
- Week 1: Discovery
- Week 2-3: Design
- Week 4-6: Delivery

## Investment
${TABLE_SNIPPET}

## Terms
- Payment terms
- Delivery assumptions
- Revision policy`;

export function DocumentEditor({ content, onChange }: DocumentEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const markdown = useMemo(() => content.markdown || '', [content.markdown]);

  const setMarkdown = (nextMarkdown: string) => {
    onChange({
      ...content,
      markdown: nextMarkdown,
      blocks: undefined,
    });
  };

  const withSelection = (
    updater: (args: {
      value: string;
      selected: string;
      start: number;
      end: number;
    }) => { next: string; cursorStart?: number; cursorEnd?: number }
  ) => {
    const textarea = textareaRef.current;
    const value = markdown;
    if (!textarea) return;

    const start = textarea.selectionStart ?? value.length;
    const end = textarea.selectionEnd ?? value.length;
    const selected = value.slice(start, end);
    const result = updater({ value, selected, start, end });

    setMarkdown(result.next);

    requestAnimationFrame(() => {
      textarea.focus();
      const nextStart = result.cursorStart ?? start;
      const nextEnd = result.cursorEnd ?? nextStart;
      textarea.setSelectionRange(nextStart, nextEnd);
    });
  };

  const wrapSelection = (before: string, after: string, fallback: string) => {
    withSelection(({ value, selected, start, end }) => {
      const text = selected || fallback;
      const replacement = `${before}${text}${after}`;
      const next = `${value.slice(0, start)}${replacement}${value.slice(end)}`;
      const cursorStart = start + before.length;
      const cursorEnd = cursorStart + text.length;
      return { next, cursorStart, cursorEnd };
    });
  };

  const prefixLines = (prefix: string) => {
    withSelection(({ value, selected, start, end }) => {
      const text = selected || 'Text';
      const lines = text.split('\n').map((line) => `${prefix}${line}`);
      const replacement = lines.join('\n');
      const next = `${value.slice(0, start)}${replacement}${value.slice(end)}`;
      return { next, cursorStart: start, cursorEnd: start + replacement.length };
    });
  };

  const insertBlock = (snippet: string) => {
    withSelection(({ value, start, end }) => {
      const before = value.slice(0, start);
      const after = value.slice(end);
      const needsLeadingNewline = before.length > 0 && !before.endsWith('\n\n');
      const leading = needsLeadingNewline ? '\n\n' : '';
      const needsTrailingNewline = after.length > 0 && !after.startsWith('\n\n');
      const trailing = needsTrailingNewline ? '\n\n' : '';
      const replacement = `${leading}${snippet}${trailing}`;
      const next = `${before}${replacement}${after}`;
      const caret = before.length + replacement.length;
      return { next, cursorStart: caret, cursorEnd: caret };
    });
  };

  const toolbarActions: ToolbarAction[] = [
    { id: 'h1', label: 'H1', icon: <Heading1 className="h-4 w-4" />, onClick: () => prefixLines('# ') },
    { id: 'h2', label: 'H2', icon: <Heading2 className="h-4 w-4" />, onClick: () => prefixLines('## ') },
    { id: 'bold', label: 'Bold', icon: <Bold className="h-4 w-4" />, onClick: () => wrapSelection('**', '**', 'bold text') },
    { id: 'italic', label: 'Italic', icon: <Italic className="h-4 w-4" />, onClick: () => wrapSelection('*', '*', 'italic text') },
    { id: 'code', label: 'Code', icon: <Code className="h-4 w-4" />, onClick: () => wrapSelection('`', '`', 'code') },
    { id: 'quote', label: 'Quote', icon: <Quote className="h-4 w-4" />, onClick: () => prefixLines('> ') },
    { id: 'bullet', label: 'Bullet', icon: <List className="h-4 w-4" />, onClick: () => prefixLines('- ') },
    { id: 'numbered', label: 'Numbered', icon: <ListOrdered className="h-4 w-4" />, onClick: () => prefixLines('1. ') },
    { id: 'link', label: 'Link', icon: <Link2 className="h-4 w-4" />, onClick: () => wrapSelection('[', '](https://example.com)', 'link text') },
    { id: 'hr', label: 'Divider', icon: <Minus className="h-4 w-4" />, onClick: () => insertBlock('---') },
    { id: 'table', label: 'Table', icon: <Table className="h-4 w-4" />, onClick: () => insertBlock(TABLE_SNIPPET) },
    { id: 'layout', label: '2-Column Layout', icon: <Layout className="h-4 w-4" />, onClick: () => insertBlock(ROW_LAYOUT_SNIPPET) },
  ];

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-gray-200 bg-white p-3">
        <div className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-700">
          <FileText className="h-4 w-4" />
          WYSIWYG Markdown Editor
        </div>

        <div className="mb-3 flex flex-wrap gap-1.5">
          {toolbarActions.map((action) => (
            <button
              key={action.id}
              type="button"
              onClick={action.onClick}
              className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-2 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
              title={action.label}
            >
              {action.icon}
              {action.label}
            </button>
          ))}
        </div>

        <div className="mb-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => {
              if (markdown.trim().length > 0) return;
              setMarkdown(PROPOSAL_SKELETON);
            }}
            className="rounded-md border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100"
          >
            Insert Proposal Template
          </button>
          <span className="self-center text-xs text-gray-500">
            Clean markdown only: headings, tables, text formatting, and row/column layout.
          </span>
        </div>

        <Textarea
          ref={textareaRef}
          value={markdown}
          onChange={(e) => setMarkdown(e.target.value)}
          className="min-h-[540px] font-mono text-sm leading-6"
          placeholder="# Start writing..."
        />
      </div>

      <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600">
        Tip: use markdown tables for pricing/scope sections. Use <code>:::row</code> + <code>:::column</code> only for simple layouts.
      </div>
    </div>
  );
}
