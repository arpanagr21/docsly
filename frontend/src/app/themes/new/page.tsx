'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ThemeEditor } from '@/components/editor/ThemeEditor';
import { useCreateTheme } from '@/hooks/useThemes';
import type { ThemeVariables } from '@/types';

export default function NewThemePage() {
  const router = useRouter();
  const createTheme = useCreateTheme();

  const handleSave = async (data: {
    name: string;
    variables: ThemeVariables;
    is_default: boolean;
  }) => {
    try {
      const result = await createTheme.mutateAsync(data);
      router.push(`/themes/${result.theme.id}`);
    } catch (error) {
      console.error('Failed to create theme:', error);
    }
  };

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
            <li className="text-gray-900">New Theme</li>
          </ol>
        </nav>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Create New Theme</h1>
          <p className="text-gray-600 mt-1">
            Define colors, fonts, and layout settings for your documents
          </p>
        </div>

        {/* Error Display */}
        {createTheme.error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            Failed to create theme. Please try again.
          </div>
        )}

        {/* Editor */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <ThemeEditor
            onSave={handleSave}
            isLoading={createTheme.isPending}
          />
        </div>
      </div>
    </div>
  );
}
