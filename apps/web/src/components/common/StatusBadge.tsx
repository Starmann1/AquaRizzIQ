interface Props {
  status: 'DRAFT' | 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED';
}

export default function StatusBadge({ status }: Props) {
  const colors = {
    DRAFT: 'bg-slate-100 text-slate-700 border-slate-300',
    PENDING_REVIEW: 'bg-sky-50 text-sky-700 border-sky-300',
    APPROVED: 'bg-emerald-50 text-emerald-700 border-emerald-300',
    REJECTED: 'bg-rose-50 text-rose-700 border-rose-300',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${colors[status]}`}>
      {status.replace('_', ' ')}
    </span>
  );
}
