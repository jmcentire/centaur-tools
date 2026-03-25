import { useState } from 'react';

export default function ThreadStarButton({ threadId, count, initialVoted = false }: { threadId: string; count: number; initialVoted?: boolean }) {
  const [votes, setVotes] = useState(count);
  const [voted, setVoted] = useState(initialVoted);
  const [busy, setBusy] = useState(false);

  const toggle = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (busy) return;
    setBusy(true);
    try {
      const res = await fetch(`/api/forum/threads/${threadId}/vote`, { method: voted ? 'DELETE' : 'POST' });
      if (res.status === 401) { window.location.href = '/api/auth/login'; return; }
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'already_voted') { setVoted(true); if (data.vote_count != null) setVotes(data.vote_count); }
        else if (data.status === 'not_voted') { setVoted(false); if (data.vote_count != null) setVotes(data.vote_count); }
        else { setVotes(data.vote_count ?? votes + (voted ? -1 : 1)); setVoted(!voted); }
      }
    } catch {} finally { setBusy(false); }
  };

  return (
    <button onClick={toggle} disabled={busy}
      className="flex items-center gap-1 text-secondary hover:text-emphasis transition-colors disabled:opacity-50"
      title={voted ? 'Remove vote' : 'Vote useful'}>
      <svg width={16} height={16} viewBox="0 0 24 24" fill={voted ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
      </svg>
      <span className="text-[13px] tabular-nums">{votes}</span>
    </button>
  );
}
