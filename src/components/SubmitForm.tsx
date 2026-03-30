import { useState } from 'react';
import { motion } from 'framer-motion';

interface FormData {
  name: string;
  description: string;
  problem_statement: string;
  repo_url: string;
  language: string;
  tags: string;
  fork_parent_slug: string;
}

const initialForm: FormData = {
  name: '',
  description: '',
  problem_statement: '',
  repo_url: '',
  language: '',
  tags: '',
  fork_parent_slug: '',
};

export default function SubmitForm() {
  const [form, setForm] = useState<FormData>(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState<string | null>(null);

  const update = (field: keyof FormData) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    if (!form.name.trim() || !form.description.trim() || !form.problem_statement.trim()) {
      setError('Name, description, and problem statement are required.');
      setSubmitting(false);
      return;
    }

    if (!form.repo_url.trim()) {
      setError('Repository URL is required.');
      setSubmitting(false);
      return;
    }

    try {
      const payload = {
        name: form.name.trim(),
        description: form.description.trim(),
        problem_statement: form.problem_statement.trim(),
        repo_url: form.repo_url.trim(),
        language: form.language.trim(),
        tags: form.tags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
        fork_parent_slug: form.fork_parent_slug.trim() || undefined,
      };

      const res = await fetch('/api/tools/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.status === 401) {
        window.location.href = '/api/auth/login';
        return;
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.message || 'Submission failed');
      }

      const tool = await res.json();
      setSuccess(tool.slug);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <motion.div
        className="max-w-2xl mx-auto px-6 text-center py-20"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="w-16 h-16 rounded-full bg-surface flex items-center justify-center mx-auto mb-6">
          <svg className="w-8 h-8 text-emphasis" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-primary mb-3">Tool submitted</h2>
        <p className="text-secondary text-sm mb-8">
          Your tool has been registered in the centaur registry. The proximity engine will find your neighbors.
        </p>
        <a
          href={`/tools/${success}`}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-emphasis font-medium text-sm rounded-md hover:opacity-90 transition-opacity no-underline"
          style={{ color: '#ffffff' }}
        >
          View your tool
        </a>
      </motion.div>
    );
  }

  return (
    <motion.div
      className="max-w-2xl mx-auto px-6"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* MIT License notice */}
      <div className="p-5 rounded border border-rule mb-10">
        <div className="flex items-start gap-3">
          <svg className="w-5 h-5 text-secondary shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
            />
          </svg>
          <div>
            <h3 className="font-semibold text-primary text-sm mb-1">MIT License Required</h3>
            <p className="text-secondary text-xs leading-relaxed">
              All tools on centaur.tools must be MIT licensed. Full stop. No exceptions. Everything here is forkable, stealable, buildable-upon. By submitting, you confirm your tool uses the MIT license.
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Name */}
        <div>
          <label className="text-[13px] text-secondary block mb-2">
            Tool Name <span className="text-emphasis">*</span>
          </label>
          <input
            type="text"
            value={form.name}
            onChange={update('name')}
            placeholder="e.g., kindex"
            required
            className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors placeholder:text-quiet"
          />
        </div>

        {/* Description */}
        <div>
          <label className="text-[13px] text-secondary block mb-2">
            Short Description <span className="text-emphasis">*</span>
          </label>
          <input
            type="text"
            value={form.description}
            onChange={update('description')}
            placeholder="One-liner about what it does"
            required
            className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors placeholder:text-quiet"
          />
        </div>

        {/* Problem statement */}
        <div>
          <label className="text-[13px] text-secondary block mb-2">
            Problem Statement <span className="text-emphasis">*</span>
          </label>
          <p className="text-quiet text-xs mb-2">
            What problem does this solve? This is used for proximity matching with other tools.
          </p>
          <textarea
            value={form.problem_statement}
            onChange={update('problem_statement')}
            placeholder="Describe the problem your tool addresses..."
            rows={4}
            required
            className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors placeholder:text-quiet resize-none"
          />
        </div>

        {/* Repo URL */}
        <div>
          <label className="text-[13px] text-secondary block mb-2">
            Repository URL <span className="text-emphasis">*</span>
          </label>
          <input
            type="url"
            value={form.repo_url}
            onChange={update('repo_url')}
            placeholder="https://github.com/..."
            required
            className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors placeholder:text-quiet"
          />
        </div>

        {/* Language */}
        <div>
          <label className="text-[13px] text-secondary block mb-2">Language</label>
          <input
            type="text"
            value={form.language}
            onChange={update('language')}
            placeholder="e.g., Python, TypeScript, Rust"
            className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors placeholder:text-quiet"
          />
        </div>

        {/* Tags */}
        <div>
          <label className="text-[13px] text-secondary block mb-2">Tags</label>
          <p className="text-quiet text-xs mb-2">Comma-separated list of tags</p>
          <input
            type="text"
            value={form.tags}
            onChange={update('tags')}
            placeholder="knowledge-graph, mcp, memory, ai-tools"
            className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors placeholder:text-quiet"
          />
        </div>

        {/* Related projects */}
        <div>
          <label className="text-[13px] text-secondary block mb-2">
            Related Projects <span className="text-quiet">(optional)</span>
          </label>
          <p className="text-quiet text-xs mb-2">
            Slugs of related tools on centaur.tools, comma-separated
          </p>
          <input
            type="text"
            value={form.fork_parent_slug}
            onChange={update('fork_parent_slug')}
            placeholder="kindex, signet"
            className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors placeholder:text-quiet"
          />
        </div>

        {/* Error */}
        {error && (
          <div className="p-4 rounded border border-error/30 bg-error/5">
            <p className="text-error text-sm">{error}</p>
          </div>
        )}

        {/* Submit */}
        <div className="pt-4">
          <button
            type="submit"
            disabled={submitting}
            className="w-full px-5 py-2.5 bg-emphasis text-on-emphasis font-medium text-sm rounded-md hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {submitting ? 'Submitting...' : 'Register Tool'}
          </button>
          <p className="text-quiet text-xs text-center mt-3">
            By submitting, you confirm this tool is MIT licensed.
          </p>
        </div>
      </form>
    </motion.div>
  );
}
