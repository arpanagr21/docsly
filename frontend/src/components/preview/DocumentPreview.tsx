'use client';

import React from 'react';

export interface DocumentPreviewProps {
  html?: string;
  isLoading?: boolean;
  error?: string | null;
}

export function DocumentPreview({ html, isLoading = false, error = null }: DocumentPreviewProps) {
  if (isLoading) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>Rendering preview...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (!html) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>No preview available.</p>
      </div>
    );
  }

  return (
    <iframe
      title="Document Preview"
      srcDoc={html}
      className="w-full min-h-[70vh] border border-gray-200 rounded-md bg-white"
      sandbox="allow-same-origin"
    />
  );
}
