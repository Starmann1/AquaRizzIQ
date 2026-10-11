interface Props {
  level: string;
}

export default function RiskBadge({ level }: Props) {
  const normLevel = (level?.toUpperCase() || 'UNKNOWN');
  const colors: Record<string, string> = {
    LOW: 'bg-emerald-50 text-emerald-700 border-emerald-300 font-semibold',
    MEDIUM: 'bg-amber-50 text-amber-800 border-amber-300 font-semibold',
    HIGH: 'bg-orange-50 text-orange-800 border-orange-300 font-semibold',
    VERY_HIGH: 'bg-rose-50 text-rose-800 border-rose-300 font-semibold',
    INSUFFICIENT_EVIDENCE: 'bg-slate-100 text-slate-700 border-slate-300',
    UNKNOWN: 'bg-slate-100 text-slate-500 border-slate-300',
  };

  const colorClass = colors[normLevel] || colors.UNKNOWN;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs border shadow-xs ${colorClass}`}>
      {level ? level.replace('_', ' ') : 'UNKNOWN'}
    </span>
  );
}
