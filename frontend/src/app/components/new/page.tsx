'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ComponentEditor } from '@/components/editor/ComponentEditor';
import { useCreateComponent } from '@/hooks/useComponents';
import type { JSONSchema } from '@/types';

export default function NewComponentPage() {
  const router = useRouter();
  const createComponent = useCreateComponent();

  const handleSave = async (data: { name: string; schema: JSONSchema; template: string }) => {
    try {
      const result = await createComponent.mutateAsync(data);
      router.push(`/components/${result.component.id}`);
    } catch (error) {
      console.error('Failed to create component:', error);
    }
  };

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
            <li className="text-gray-900">New Component</li>
          </ol>
        </nav>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Create New Component</h1>
          <p className="text-gray-600 mt-1">
            Define a reusable component with a JSON schema and Markdown template
          </p>
        </div>

        {/* Error Display */}
        {createComponent.error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            Failed to create component. Please try again.
          </div>
        )}

        {/* Editor */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <ComponentEditor
            onSave={handleSave}
            isLoading={createComponent.isPending}
          />
        </div>
      </div>
    </div>
  );
}
