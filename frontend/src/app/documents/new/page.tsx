'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCreateDocument } from '@/hooks/useDocument';
import { ArrowLeft, Loader2 } from 'lucide-react';
import Link from 'next/link';

export default function NewDocumentPage() {
  const router = useRouter();
  const { create, isCreating, error } = useCreateDocument();
  const [title, setTitle] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!title.trim()) {
      return;
    }

    try {
      const result = await create({
        title: title.trim(),
        content: {
          version: '2.0',
          theme_id: null,
          markdown: '',
        },
      });
      router.push(`/documents/${result.document.id}`);
    } catch (err) {
      // Error is handled by the mutation
      console.error('Failed to create document:', err);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <Link
        href="/documents"
        className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Documents
      </Link>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Create New Document</h1>

        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
              Document Title
            </label>
            <input
              type="text"
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter a title for your document"
              className="w-full border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              autoFocus
            />
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
              {error.message || 'Failed to create document. Please try again.'}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <Link
              href="/documents"
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={isCreating || !title.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2"
            >
              {isCreating && <Loader2 className="w-4 h-4 animate-spin" />}
              {isCreating ? 'Creating...' : 'Create Document'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
