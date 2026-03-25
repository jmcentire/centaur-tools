import { useState, useEffect } from 'react';

interface ToolData {
  slug: string;
  name: string;
  description: string;
  problem_statement: string;
  repo_url: string;
  language: string;
  tags: string[];
  author: { username: string };
}

export default function EditForm({ slug }: { slug: string }) {
  const [tool, setTool] = useState<ToolData | null>(null);
  const [description, setDescription] = useState('');
  const [problemStatement, setProblemStatement] = useState('');
  const [repoUrl, setRepoUrl] = useState('');
  const [language, setLanguage] = useState('');
  const [tags, setTags] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`/api/tools/${slug}`)
      .then(r => {
        if (!r.ok) throw new Error('Tool not found');
        return r.json();
      })
      .then(data => {
        setTool(data);
        setDescription(data.description);
        setProblemStatement(data.problem_statement);
        setRepoUrl(data.repo_url);
        setLanguage(data.language || '');
        setTags((data.tags || []).join(', '));
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [slug]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSaved(false);

    try {
      const res = await fetch(`/api/tools/${slug}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description,
          problem_statement: problemStatement,
          repo_url: repoUrl,
          language: language || null,
          tags: tags.split(',').map(t => t.trim()).filter(Boolean),
        }),
      });

      if (res.status === 401) {
        window.location.href = '/api/auth/login';
        return;
      }
      if (res.status === 403) {
        setError('You can only edit your own tools.');
        return;
      }
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to save');
      }

      setSaved(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="text-secondary py-16 text-center">Loading...</p>;
  if (error && !tool) return (
    <div className="py-16 text-center">
      <p className="text-body mb-3">{error}</p>
      <a href="/dashboard" className="text-sm text-emphasis hover:opacity-70 transition-opacity">Back to dashboard</a>
    </div>
  );
  if (!tool) return null;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-[13px] text-secondary mb-1">Name</label>
        <p className="text-primary font-semibold">{tool.name}</p>
        <p className="text-[13px] text-quiet mt-1">Tool names cannot be changed after registration.</p>
      </div>

      <div>
        <label className="block text-[13px] text-secondary mb-1">Description</label>
        <input
          type="text"
          value={description}
          onChange={e => setDescription(e.target.value)}
          className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors"
        />
      </div>

      <div>
        <label className="block text-[13px] text-secondary mb-1">Problem statement</label>
        <textarea
          value={problemStatement}
          onChange={e => setProblemStatement(e.target.value)}
          rows={5}
          className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors resize-none"
        />
      </div>

      <div>
        <label className="block text-[13px] text-secondary mb-1">Repository URL</label>
        <input
          type="url"
          value={repoUrl}
          onChange={e => setRepoUrl(e.target.value)}
          className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors"
        />
      </div>

      <div>
        <label className="block text-[13px] text-secondary mb-1">Language</label>
        <input
          type="text"
          value={language}
          onChange={e => setLanguage(e.target.value)}
          className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors"
        />
      </div>

      <div>
        <label className="block text-[13px] text-secondary mb-1">Tags (comma-separated)</label>
        <input
          type="text"
          value={tags}
          onChange={e => setTags(e.target.value)}
          className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors"
        />
      </div>

      <div>
        <label className="block text-[13px] text-secondary mb-1">Related Projects <span className="text-quiet">(optional, comma-separated slugs)</span></label>
        <input
          type="text"
          placeholder="kindex, signet"
          className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors placeholder:text-quiet"
        />
        <p className="text-quiet text-xs mt-1">Slugs of related tools on centaur.tools</p>
      </div>

      {error && <p className="text-error text-sm">{error}</p>}
      {saved && <p className="text-success text-sm">Changes saved.</p>}

      <div className="flex items-center gap-4">
        <button
          type="submit"
          disabled={saving}
          className="px-5 py-2.5 bg-emphasis text-on-emphasis font-medium text-sm rounded-md hover:opacity-90 transition-opacity disabled:opacity-40"
        >
          {saving ? 'Saving...' : 'Save changes'}
        </button>
        <a href={`/tools/${slug}`} className="text-sm text-secondary hover:text-primary transition-colors">
          Cancel
        </a>
      </div>
    </form>
  );
}
