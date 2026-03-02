'use client';

import Link from 'next/link';
import { useComponents } from '@/hooks/useComponents';
import { Badge } from '@/components/ui/badge';
import type { Component } from '@/types';

function ComponentCard({ component }: { component: Component }) {
  return (
    <Link
      href={`/components/${component.id}`}
      className="block p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md hover:border-gray-300 transition-all"
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-lg font-semibold text-gray-900">{component.name}</h3>
        <div className="flex gap-2">
          {component.is_builtin && (
            <Badge variant="secondary">Built-in</Badge>
          )}
          <Badge variant="default">v{component.version}</Badge>
        </div>
      </div>
      <div className="text-sm text-gray-500">
        <p>
          {Object.keys(component.schema?.properties || {}).length} properties
        </p>
        <p className="text-xs mt-1">
          Created: {component.created_at ? new Date(component.created_at).toLocaleDateString() : 'Unknown'}
        </p>
      </div>
    </Link>
  );
}

export default function ComponentsPage() {
  const { data: components, isLoading, error } = useComponents();

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="max-w-6xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 w-48 bg-gray-200 rounded mb-6" />
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-32 bg-gray-200 rounded-lg" />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="max-w-6xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            Failed to load components. Please try again later.
          </div>
        </div>
      </div>
    );
  }

  const builtinComponents = components?.filter((c) => c.is_builtin) || [];
  const userComponents = components?.filter((c) => !c.is_builtin) || [];

  return (
    <div className="p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Component Library</h1>
            <p className="text-gray-600 mt-1">
              Manage your document components
            </p>
          </div>
          <Link
            href="/components/new"
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            New Component
          </Link>
        </div>

        {/* Built-in Components */}
        {builtinComponents.length > 0 && (
          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">
              Built-in Components
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {builtinComponents.map((component) => (
                <ComponentCard key={component.id} component={component} />
              ))}
            </div>
          </section>
        )}

        {/* User Components */}
        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Your Components
          </h2>
          {userComponents.length === 0 ? (
            <div className="text-center py-12 bg-white border border-gray-200 rounded-lg">
              <p className="text-gray-500 mb-4">
                You haven't created any components yet.
              </p>
              <Link
                href="/components/new"
                className="text-blue-600 hover:text-blue-700 font-medium"
              >
                Create your first component
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {userComponents.map((component) => (
                <ComponentCard key={component.id} component={component} />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
