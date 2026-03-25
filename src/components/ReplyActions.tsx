import { useState, useEffect } from 'react';

export default function ReplyActions({
  replyId,
  body,
  authorUsername,
}: {
  replyId: string;
  body: string;
  authorUsername: string;
}) {
  const [isOwner, setIsOwner] = useState(false);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editBody, setEditBody] = useState(body);

  useEffect(() => {
    fetch('/api/auth/me')
      .then((r) => (r.ok ? r.json() : null))
      .then((me) => {
        if (me && me.username === authorUsername) setIsOwner(true);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [authorUsername]);

  if (loading || !isOwner) return null;

  const handleSave = async () => {
    const res = await fetch(`/api/forum/replies/${replyId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ body: editBody }),
    });
    if (res.ok) window.location.reload();
  };

  const handleDelete = async () => {
    if (!confirm('Delete this reply?')) return;
    const res = await fetch(`/api/forum/replies/${replyId}`, {
      method: 'DELETE',
    });
    if (res.ok) window.location.reload();
  };

  if (editing) {
    return (
      <div className="space-y-2 mt-2">
        <textarea
          value={editBody}
          onChange={(e) => setEditBody(e.target.value)}
          rows={3}
          className="w-full px-4 py-2.5 bg-surface border border-rule rounded text-primary text-base focus:outline-none focus:border-emphasis transition-colors resize-none"
        />
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            className="px-3 py-1.5 bg-emphasis text-on-emphasis text-sm rounded-md hover:opacity-90 transition-opacity"
          >
            Save
          </button>
          <button
            onClick={() => {
              setEditing(false);
              setEditBody(body);
            }}
            className="text-sm text-secondary hover:text-primary transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 mt-1">
      <button
        onClick={() => setEditing(true)}
        className="text-[13px] text-secondary hover:text-primary transition-colors"
      >
        Edit
      </button>
      <button
        onClick={handleDelete}
        className="text-[13px] text-secondary hover:text-error transition-colors"
      >
        Delete
      </button>
    </div>
  );
}
