'use client';

import { useState, useEffect } from 'react';
import { oauthService } from '@/lib/api/services/oauth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Key, Plus, Trash2, RefreshCw, Copy, Check, AlertCircle } from 'lucide-react';
import type { OAuthClient } from '@/types';

export default function SettingsPage() {
  const [clients, setClients] = useState<OAuthClient[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newClientName, setNewClientName] = useState('');
  const [newlyCreatedClient, setNewlyCreatedClient] = useState<OAuthClient | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [regeneratingId, setRegeneratingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadClients();
  }, []);

  const loadClients = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await oauthService.listClients();
      setClients(response.clients);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateClient = async () => {
    if (!newClientName.trim()) return;

    try {
      setCreating(true);
      setError(null);
      const response = await oauthService.createClient({ name: newClientName.trim() });
      setNewlyCreatedClient(response.client);
      setNewClientName('');
      await loadClients();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create API key');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteClient = async (id: number) => {
    if (!confirm('Are you sure you want to delete this API key? This action cannot be undone.')) {
      return;
    }

    try {
      setDeletingId(id);
      setError(null);
      await oauthService.deleteClient(id);
      setClients(clients.filter(c => c.id !== id));
      if (newlyCreatedClient?.id === id) {
        setNewlyCreatedClient(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete API key');
    } finally {
      setDeletingId(null);
    }
  };

  const handleRegenerateSecret = async (id: number) => {
    if (!confirm('Are you sure you want to regenerate this API key secret? The old secret will stop working immediately.')) {
      return;
    }

    try {
      setRegeneratingId(id);
      setError(null);
      const response = await oauthService.regenerateSecret(id);
      setNewlyCreatedClient(response.client);
      await loadClients();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to regenerate secret');
    } finally {
      setRegeneratingId(null);
    }
  };

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
        <p className="text-gray-600 mt-1">
          Manage your OAuth credentials for MCP integrations. These keys allow AI assistants like Claude or ChatGPT to access your documents.
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-red-700">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* New Client Secret Display */}
      {newlyCreatedClient?.client_secret && (
        <Card className="mb-6 p-6 bg-amber-50 border-amber-200">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="font-semibold text-amber-800">Save your API key secret</h3>
              <p className="text-sm text-amber-700 mt-1 mb-4">
                This is the only time you'll see this secret. Copy it now and store it securely.
              </p>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-amber-800 mb-1">Client ID</label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 bg-white px-3 py-2 rounded border border-amber-200 text-sm font-mono break-all">
                      {newlyCreatedClient.client_id}
                    </code>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(newlyCreatedClient.client_id, 'new-client-id')}
                      className="flex-shrink-0"
                    >
                      {copiedField === 'new-client-id' ? (
                        <Check className="w-4 h-4 text-green-600" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-amber-800 mb-1">Client Secret</label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 bg-white px-3 py-2 rounded border border-amber-200 text-sm font-mono break-all">
                      {newlyCreatedClient.client_secret}
                    </code>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(newlyCreatedClient.client_secret!, 'new-client-secret')}
                      className="flex-shrink-0"
                    >
                      {copiedField === 'new-client-secret' ? (
                        <Check className="w-4 h-4 text-green-600" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </div>

              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => setNewlyCreatedClient(null)}
              >
                I've saved my secret
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Create New Client */}
      <Card className="mb-6 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Plus className="w-5 h-5" />
          Create New API Key
        </h2>
        <div className="flex gap-3">
          <Input
            placeholder="API key name (e.g., 'Claude Desktop', 'ChatGPT')"
            value={newClientName}
            onChange={(e) => setNewClientName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreateClient()}
            className="flex-1"
          />
          <Button
            onClick={handleCreateClient}
            disabled={creating || !newClientName.trim()}
          >
            {creating ? 'Creating...' : 'Create'}
          </Button>
        </div>
      </Card>

      {/* Existing Clients */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <Key className="w-5 h-5" />
          Your API Keys
        </h2>

        {loading ? (
          <div className="text-center py-8 text-gray-500">Loading...</div>
        ) : clients.length === 0 ? (
          <Card className="p-8 text-center text-gray-500">
            <Key className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No API keys yet. Create one to get started.</p>
          </Card>
        ) : (
          <div className="space-y-3">
            {clients.map((client) => (
              <Card key={client.id} className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-medium text-gray-900">{client.name}</h3>
                      {!client.is_active && (
                        <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">
                          Inactive
                        </span>
                      )}
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500 w-20">Client ID:</span>
                        <code className="text-xs bg-gray-100 px-2 py-1 rounded font-mono flex-1 truncate">
                          {client.client_id}
                        </code>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(client.client_id, `client-id-${client.id}`)}
                          className="h-6 w-6 p-0"
                        >
                          {copiedField === `client-id-${client.id}` ? (
                            <Check className="w-3 h-3 text-green-600" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </Button>
                      </div>

                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>Created: {formatDate(client.created_at)}</span>
                        <span>|</span>
                        <span>Last used: {formatDate(client.last_used_at)}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRegenerateSecret(client.id)}
                      disabled={regeneratingId === client.id}
                      title="Regenerate secret"
                    >
                      <RefreshCw className={`w-4 h-4 ${regeneratingId === client.id ? 'animate-spin' : ''}`} />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeleteClient(client.id)}
                      disabled={deletingId === client.id}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      title="Delete API key"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Usage Instructions */}
      <Card className="mt-8 p-6 bg-blue-50 border-blue-200">
        <h3 className="font-semibold text-blue-900 mb-3">How to use with Claude Code / Claude Desktop</h3>
        <div className="text-sm text-blue-800 space-y-3">
          <p>Add this to your Claude Code MCP settings (<code className="bg-blue-100 px-1 rounded">~/.claude/claude_desktop_config.json</code>):</p>

          <pre className="bg-white p-3 rounded border border-blue-200 overflow-x-auto text-xs">
{`{
  "mcpServers": {
    "docsly": {
      "url": "${typeof window !== 'undefined' ? window.location.origin.replace(':3000', ':5001') : 'http://localhost:5001'}/mcp",
      "auth": {
        "type": "oauth",
        "client_id": "<YOUR_CLIENT_ID>",
        "client_secret": "<YOUR_CLIENT_SECRET>",
        "token_url": "${typeof window !== 'undefined' ? window.location.origin.replace(':3000', ':5001') : 'http://localhost:5001'}/oauth/token"
      }
    }
  }
}`}
          </pre>

          <p className="mt-4"><strong>Or use curl to get an access token:</strong></p>
          <pre className="bg-white p-3 rounded border border-blue-200 overflow-x-auto text-xs">
{`curl -X POST ${typeof window !== 'undefined' ? window.location.origin.replace(':3000', ':5001') : 'http://localhost:5001'}/oauth/token \\
  -H "Content-Type: application/json" \\
  -d '{"grant_type": "client_credentials", "client_id": "<YOUR_CLIENT_ID>", "client_secret": "<YOUR_CLIENT_SECRET>"}'`}
          </pre>

          <p className="text-xs text-blue-600 mt-3">
            The access token is valid for 90 days. Use the returned <code>refresh_token</code> to get a new access token when it expires.
          </p>
        </div>
      </Card>
    </div>
  );
}
