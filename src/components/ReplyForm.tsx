import { useState } from 'react';

export default function ReplyForm({ threadId }: { threadId: string }) {
  const [body, setBody] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!body.trim()) return;
    setSubmitting(true);
    setError('');
    try {
      const res = await fetch(`/api/forum/threads/${threadId}/replies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: body.trim() }),
      });
      if (res.status === 401) {
        window.location.href = '/api/auth/login';
        return;
      }
      if (!res.ok) throw new Error('Failed to post reply');
      window.location.reload();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Write a reply..."
        rows={4}
        className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors placeholder:text-quiet resize-none"
      />
      {error && <p className="text-error text-sm">{error}</p>}
      <button
        type="submit"
        disabled={submitting || !body.trim()}
        className="px-5 py-2.5 bg-emphasis text-on-emphasis font-medium text-sm rounded-md hover:opacity-90 transition-opacity disabled:opacity-40"
      >
        {submitting ? 'Posting...' : 'Reply'}
      </button>
    </form>
  );
}
