'use client';

import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ComponentEditor } from '@/components/editor/ComponentEditor';
import { Badge } from '@/components/ui/badge';
import { useComponent, useUpdateComponent, useDeleteComponent } from '@/hooks/useComponents';
import type { JSONSchema } from '@/types';

export default function EditComponentPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const { data: component, isLoading, error } = useComponent(id);
  const updateComponent = useUpdateComponent();
  const deleteComponent = useDeleteComponent();

  const handleSave = async (data: { name: string; schema: JSONSchema; template: string }) => {
    try {
      await updateComponent.mutateAsync({ id, data });
    } catch (error) {
      console.error('Failed to update component:', error);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this component?')) {
      return;
    }

    try {
      await deleteComponent.mutateAsync(id);
      router.push('/components');
    } catch (error) {
      console.error('Failed to delete component:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="animate-pulse">
            <div className="h-6 w-32 bg-gray-200 rounded mb-6" />
            <div className="h-10 w-64 bg-gray-200 rounded mb-8" />
            <div className="bg-white rounded-lg p-6 space-y-4">
              <div className="h-10 bg-gray-200 rounded" />
              <div className="h-32 bg-gray-200 rounded" />
              <div className="h-48 bg-gray-200 rounded" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !component) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            Component not found or failed to load.
            <Link href="/components" className="ml-2 underline">
              Go back to components
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Breadcrumb */}
        <nav className="mb-6">
          <ol className="flex items-center space-x-2 text-sm text-gray-500">
            <li>
              <Link href="/components" className="hover:text-gray-700">
                Components
              </Link>
            </li>
            <li>/</li>
            <li className="text-gray-900">{component.name}</li>
          </ol>
        </nav>

        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900">{component.name}</h1>
              <Badge variant="default">v{component.version}</Badge>
              {component.is_builtin && (
                <Badge variant="secondary">Built-in</Badge>
              )}
            </div>
            <p className="text-gray-600">
              {component.is_builtin
                ? 'This is a built-in component and cannot be modified.'
                : 'Edit your component schema and template below.'}
            </p>
          </div>

          {!component.is_builtin && (
            <button
              onClick={handleDelete}
              disabled={deleteComponent.isPending}
              className="px-4 py-2 text-red-600 border border-red-300 rounded-md hover:bg-red-50 transition-colors disabled:opacity-50"
            >
              {deleteComponent.isPending ? 'Deleting...' : 'Delete'}
            </button>
          )}
        </div>

        {/* Version History */}
        <div className="bg-gray-100 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Version Info</h3>
          <div className="flex gap-4 text-sm text-gray-600">
            <span>Current Version: {component.version}</span>
            <span>|</span>
            <span>
              Created: {component.created_at ? new Date(component.created_at).toLocaleDateString() : 'Unknown'}
            </span>
          </div>
        </div>

        {/* Error Display */}
        {(updateComponent.error || deleteComponent.error) && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            An error occurred. Please try again.
          </div>
        )}

        {/* Success Message */}
        {updateComponent.isSuccess && (
          <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4 text-green-700">
            Component updated successfully! A new version has been created.
          </div>
        )}

        {/* Editor */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <ComponentEditor
            component={component}
            onSave={handleSave}
            isLoading={updateComponent.isPending}
          />
        </div>
      </div>
    </div>
  );
}
