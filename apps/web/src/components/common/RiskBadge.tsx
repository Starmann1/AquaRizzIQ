interface Props {
  level: string;
}

export default function RiskBadge({ level }: Props) {
  const normLevel = (level?.toUpperCase() || 'UNKNOWN');
  const colors: Record<string, string> = {
    LOW: 'bg-green-900/50 text-green-300 border-green-600/50',
    MEDIUM: 'bg-yellow-900/50 text-yellow-300 border-yellow-600/50',
    HIGH: 'bg-orange-900/50 text-orange-300 border-orange-600/50',
    VERY_HIGH: 'bg-red-900/50 text-red-300 border-red-600/50',
    UNKNOWN: 'bg-slate-800 text-slate-400 border-slate-700',
  };

  const colorClass = colors[normLevel] || colors.UNKNOWN;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}>
      {level ? level.replace('_', ' ') : 'UNKNOWN'}
    </span>
  );
}
