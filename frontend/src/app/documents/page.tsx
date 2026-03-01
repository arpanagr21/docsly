'use client';

import React from 'react';
import Link from 'next/link';
import { useDocuments } from '@/hooks/useDocument';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { FileText, Plus, Loader2 } from 'lucide-react';
import type { Document } from '@/types/document';

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

interface DocumentCardProps {
  document: Document;
}

function DocumentCard({ document }: DocumentCardProps) {
  return (
    <Link href={`/documents/${document.id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <div className="min-w-0 flex-1">
              <CardTitle className="truncate">{document.title || 'Untitled'}</CardTitle>
              <CardDescription className="mt-1">
                Updated {formatDate(document.updated_at)}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">
            {(document.content.markdown || '').trim().length > 0
              ? `${(document.content.markdown || '').trim().split(/\s+/).length} words`
              : 'Empty document'}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-12">
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <FileText className="w-8 h-8 text-gray-400" />
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-1">No documents yet</h3>
      <p className="text-gray-500 mb-4">Get started by creating your first document.</p>
      <Link
        href="/documents/new"
        className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
      >
        <Plus className="w-4 h-4" />
        New Document
      </Link>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center py-12">
      <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
    </div>
  );
}

export default function DocumentsPage() {
  const { documents, isLoading, error } = useDocuments();

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
          <p className="text-gray-500 mt-1">Create and manage your documents</p>
        </div>
        <Link
          href="/documents/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Document
        </Link>
      </div>

      {isLoading ? (
        <LoadingState />
      ) : error ? (
        <div className="text-center py-12 text-red-500">
          <p>Error loading documents. Please try again.</p>
        </div>
      ) : documents.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {documents.map((document) => (
            <DocumentCard key={document.id} document={document} />
          ))}
        </div>
      )}
    </div>
  );
}
