'use client';

import Link from 'next/link';
import { useThemes } from '@/hooks/useThemes';
import { Badge } from '@/components/ui/badge';
import type { Theme } from '@/types';

function ColorSwatch({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5" title={label}>
      <div
        className="w-4 h-4 rounded border border-gray-200"
        style={{ backgroundColor: color }}
      />
    </div>
  );
}

function ThemeCard({ theme }: { theme: Theme }) {
  const variables = theme.variables || {};
  const textColor = String(variables['text-color'] || '#1f2937');
  const bgColor = String(variables['background-color'] || '#ffffff');
  const primaryColor = String(variables['primary-color'] || '#3b82f6');

  return (
    <Link
      href={`/themes/${theme.id}`}
      className="block p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md hover:border-gray-300 transition-all"
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-900">{theme.name}</h3>
        <div className="flex gap-2">
          {theme.is_default && (
            <Badge variant="success">Default</Badge>
          )}
          {theme.is_builtin && (
            <Badge variant="secondary">Built-in</Badge>
          )}
        </div>
      </div>

      {/* Color Swatches */}
      <div className="flex gap-3 mb-3">
        <ColorSwatch color={textColor} label="Text Color" />
        <ColorSwatch color={bgColor} label="Background Color" />
        <ColorSwatch color={primaryColor} label="Primary Color" />
      </div>

      {/* Preview Bar */}
      <div
        className="h-8 rounded flex items-center justify-center text-sm"
        style={{
          backgroundColor: bgColor,
          color: textColor,
          border: '1px solid #e5e7eb',
        }}
      >
        <span style={{ color: primaryColor }}>Aa</span>
        <span className="mx-2">Sample Text</span>
      </div>

      <p className="text-xs text-gray-500 mt-2">
        Created: {theme.created_at ? new Date(theme.created_at).toLocaleDateString() : 'Unknown'}
      </p>
    </Link>
  );
}

export default function ThemesPage() {
  const { data: themes, isLoading, error } = useThemes();

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="max-w-6xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 w-32 bg-gray-200 rounded mb-6" />
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-40 bg-gray-200 rounded-lg" />
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
            Failed to load themes. Please try again later.
          </div>
        </div>
      </div>
    );
  }

  const builtinThemes = themes?.filter((t) => t.is_builtin) || [];
  const userThemes = themes?.filter((t) => !t.is_builtin) || [];

  return (
    <div className="p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Themes</h1>
            <p className="text-gray-600 mt-1">
              Customize the look and feel of your documents
            </p>
          </div>
          <Link
            href="/themes/new"
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            New Theme
          </Link>
        </div>

        {/* Built-in Themes */}
        {builtinThemes.length > 0 && (
          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">
              Built-in Themes
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {builtinThemes.map((theme) => (
                <ThemeCard key={theme.id} theme={theme} />
              ))}
            </div>
          </section>
        )}

        {/* User Themes */}
        <section>
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Your Themes
          </h2>
          {userThemes.length === 0 ? (
            <div className="text-center py-12 bg-white border border-gray-200 rounded-lg">
              <p className="text-gray-500 mb-4">
                You haven't created any themes yet.
              </p>
              <Link
                href="/themes/new"
                className="text-blue-600 hover:text-blue-700 font-medium"
              >
                Create your first theme
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {userThemes.map((theme) => (
                <ThemeCard key={theme.id} theme={theme} />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
