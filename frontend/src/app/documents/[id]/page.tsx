'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useDocument } from '@/hooks/useDocument';
import { documentService } from '@/lib/api/services/documents';
import { useThemes } from '@/hooks/useThemes';
import { DocumentEditor } from '@/components/editor/DocumentEditor';
import { DocumentPreview } from '@/components/preview/DocumentPreview';
import { ArrowLeft, Save, Trash2, Loader2, Eye, Edit3 } from 'lucide-react';
import type { DocumentContent } from '@/types/document';

function blockToMarkdown(block: { type?: string; content?: string; name?: string; props?: Record<string, unknown> }): string {
  if (block.type === 'markdown') {
    return block.content || '';
  }

  if (block.type === 'component' && block.name) {
    const props = block.props || {};
    if (Object.keys(props).length > 0) {
      const payload = JSON.stringify(props).replace(/'/g, "\\'");
      return `{{< ${block.name} props_json='${payload}' >}}`;
    }
    return `{{< ${block.name} >}}`;
  }

  return '';
}

function normalizeDocumentContent(content: DocumentContent): DocumentContent {
  if (typeof content?.markdown === 'string') {
    return {
      ...content,
      version: content.version || '2.0',
      theme_id: content.theme_id ?? null,
      markdown: content.markdown,
    };
  }

  const blocks = Array.isArray(content?.blocks) ? content.blocks : [];
  return {
    version: '2.0',
    theme_id: content?.theme_id ?? null,
    markdown: blocks.map((block) => blockToMarkdown(block)).filter(Boolean).join('\n\n'),
  };
}

export default function DocumentEditorPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = Number(params.id);

  const {
    document,
    isLoading,
    error,
    save,
    isSaving,
    delete: deleteDocument,
    isDeleting,
  } = useDocument(documentId);
  const { data: themes } = useThemes();

  const [title, setTitle] = useState('');
  const [content, setContent] = useState<DocumentContent>({
    version: '2.0',
    theme_id: null,
    markdown: '',
  });
  const [hasChanges, setHasChanges] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [activeTab, setActiveTab] = useState<'editor' | 'preview'>('editor');
  const [previewHtml, setPreviewHtml] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Initialize state when document loads
  useEffect(() => {
    if (document) {
      setTitle(document.title);
      setContent(normalizeDocumentContent(document.content));
      setHasChanges(false);
    }
  }, [document]);

  const handleTitleChange = (newTitle: string) => {
    setTitle(newTitle);
    setHasChanges(true);
  };

  const handleContentChange = useCallback((newContent: DocumentContent) => {
    setContent(newContent);
    setHasChanges(true);
  }, []);
  const handleThemeChange = (themeId: number | null) => {
    setContent((prev) => ({ ...prev, theme_id: themeId }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    try {
      await save({ title, content });
      setHasChanges(false);
    } catch (err) {
      console.error('Failed to save document:', err);
    }
  };

  const handleDelete = async () => {
    try {
      await deleteDocument();
      router.push('/documents');
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  useEffect(() => {
    const timeout = setTimeout(async () => {
      if (!content.markdown?.trim()) {
        setPreviewHtml('');
        setPreviewError(null);
        return;
      }

      setPreviewLoading(true);
      setPreviewError(null);
      try {
        const result = await documentService.preview(content);
        setPreviewHtml(result.html);
      } catch (err) {
        setPreviewError(err instanceof Error ? err.message : 'Failed to render preview');
      } finally {
        setPreviewLoading(false);
      }
    }, 250);

    return () => clearTimeout(timeout);
  }, [content]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="p-8">
        <Link
          href="/documents"
          className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Documents
        </Link>
        <div className="text-center py-12 text-red-500">
          <p>Error loading document. It may have been deleted.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/documents"
            className="text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <input
            type="text"
            value={title}
            onChange={(e) => handleTitleChange(e.target.value)}
            className="text-xl font-semibold bg-transparent border-none focus:outline-none focus:ring-0 px-0"
            placeholder="Document title"
          />
          {hasChanges && (
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
              Unsaved changes
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            disabled={isSaving || !hasChanges}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {isSaving ? 'Saving...' : 'Save'}
          </button>
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-red-600 border border-red-200 rounded-md hover:bg-red-50 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Delete
          </button>
        </div>
      </header>

      {/* Mobile Tab Switcher */}
      <div className="lg:hidden flex border-b border-gray-200 bg-white">
        <button
          onClick={() => setActiveTab('editor')}
          className={`flex-1 py-2 px-4 text-sm font-medium flex items-center justify-center gap-2 ${
            activeTab === 'editor'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Edit3 className="w-4 h-4" />
          Editor
        </button>
        <button
          onClick={() => setActiveTab('preview')}
          className={`flex-1 py-2 px-4 text-sm font-medium flex items-center justify-center gap-2 ${
            activeTab === 'preview'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Eye className="w-4 h-4" />
          Preview
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex">
        {/* Editor Panel */}
        <div
          className={`w-full lg:w-1/2 overflow-auto border-r border-gray-200 bg-gray-50 p-4 ${
            activeTab === 'editor' ? 'block' : 'hidden lg:block'
          }`}
        >
          <div className="hidden lg:flex items-center gap-2 mb-4 text-sm font-medium text-gray-600">
            <Edit3 className="w-4 h-4" />
            Editor
          </div>
          <div className="mb-4 rounded-md border border-gray-200 bg-white p-3">
            <label className="mb-1 block text-xs font-medium text-gray-700">Theme</label>
            <select
              value={content.theme_id ?? ''}
              onChange={(e) => handleThemeChange(e.target.value ? Number(e.target.value) : null)}
              className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">No theme</option>
              {(themes || []).map((theme) => (
                <option key={theme.id} value={theme.id}>
                  {theme.name}
                </option>
              ))}
            </select>
          </div>
          <DocumentEditor content={content} onChange={handleContentChange} />
        </div>

        {/* Preview Panel */}
        <div
          className={`w-full lg:w-1/2 overflow-auto bg-white p-4 ${
            activeTab === 'preview' ? 'block' : 'hidden lg:block'
          }`}
        >
          <div className="hidden lg:flex items-center gap-2 mb-4 text-sm font-medium text-gray-600">
            <Eye className="w-4 h-4" />
            Preview
          </div>
          <DocumentPreview html={previewHtml} isLoading={previewLoading} error={previewError} />
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Delete Document
            </h3>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete "{document.title}"? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors inline-flex items-center gap-2 disabled:opacity-50"
              >
                {isDeleting && <Loader2 className="w-4 h-4 animate-spin" />}
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
