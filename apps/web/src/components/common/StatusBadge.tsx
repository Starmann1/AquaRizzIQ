interface Props {
  status: 'DRAFT' | 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED';
}

export default function StatusBadge({ status }: Props) {
  const colors = {
    DRAFT: 'bg-slate-700 text-slate-300 border-slate-600',
    PENDING_REVIEW: 'bg-blue-900/50 text-blue-300 border-blue-600/50',
    APPROVED: 'bg-green-900/50 text-green-300 border-green-600/50',
    REJECTED: 'bg-red-900/50 text-red-300 border-red-600/50',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colors[status]}`}>
      {status.replace('_', ' ')}
    </span>
  );
}
