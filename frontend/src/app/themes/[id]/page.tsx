'use client';

import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { ThemeEditor } from '@/components/editor/ThemeEditor';
import { Badge } from '@/components/ui/badge';
import { useTheme, useUpdateTheme, useDeleteTheme } from '@/hooks/useThemes';
import type { ThemeVariables } from '@/types';

export default function EditThemePage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const { data: theme, isLoading, error } = useTheme(id);
  const updateTheme = useUpdateTheme();
  const deleteTheme = useDeleteTheme();

  const handleSave = async (data: {
    name: string;
    variables: ThemeVariables;
    is_default: boolean;
  }) => {
    try {
      await updateTheme.mutateAsync({ id, data });
    } catch (error) {
      console.error('Failed to update theme:', error);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this theme?')) {
      return;
    }

    try {
      await deleteTheme.mutateAsync(id);
      router.push('/themes');
    } catch (error) {
      console.error('Failed to delete theme:', error);
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
              <div className="grid grid-cols-2 gap-4">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <div key={i} className="h-10 bg-gray-200 rounded" />
                ))}
              </div>
              <div className="h-32 bg-gray-200 rounded" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !theme) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            Theme not found or failed to load.
            <Link href="/themes" className="ml-2 underline">
              Go back to themes
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
              <Link href="/themes" className="hover:text-gray-700">
                Themes
              </Link>
            </li>
            <li>/</li>
            <li className="text-gray-900">{theme.name}</li>
          </ol>
        </nav>

        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-gray-900">{theme.name}</h1>
              {theme.is_default && (
                <Badge variant="success">Default</Badge>
              )}
              {theme.is_builtin && (
                <Badge variant="secondary">Built-in</Badge>
              )}
            </div>
            <p className="text-gray-600">
              {theme.is_builtin
                ? 'This is a built-in theme and cannot be modified.'
                : 'Edit your theme settings below.'}
            </p>
          </div>

          {!theme.is_builtin && (
            <button
              onClick={handleDelete}
              disabled={deleteTheme.isPending || theme.is_default}
              className="px-4 py-2 text-red-600 border border-red-300 rounded-md hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={theme.is_default ? 'Cannot delete the default theme' : undefined}
            >
              {deleteTheme.isPending ? 'Deleting...' : 'Delete'}
            </button>
          )}
        </div>

        {/* Theme Info */}
        <div className="bg-gray-100 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Theme Info</h3>
          <div className="flex gap-4 text-sm text-gray-600">
            <span>
              Created: {theme.created_at ? new Date(theme.created_at).toLocaleDateString() : 'Unknown'}
            </span>
            {theme.is_default && (
              <>
                <span>|</span>
                <span>This theme is applied to new documents by default</span>
              </>
            )}
          </div>
        </div>

        {/* Error Display */}
        {(updateTheme.error || deleteTheme.error) && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            An error occurred. Please try again.
          </div>
        )}

        {/* Success Message */}
        {updateTheme.isSuccess && (
          <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4 text-green-700">
            Theme updated successfully!
          </div>
        )}

        {/* Editor */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <ThemeEditor
            theme={theme}
            onSave={handleSave}
            isLoading={updateTheme.isPending}
          />
        </div>
      </div>
    </div>
  );
}
