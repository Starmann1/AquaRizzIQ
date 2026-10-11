interface Props {
  message?: string;
}

export default function ErrorDisplay({ message = 'An error occurred while loading data.' }: Props) {
  return (
    <div className="p-4 bg-rose-50/90 border border-rose-200 rounded-xl text-rose-800 shadow-xs">
      <h3 className="font-bold text-sm mb-1 text-rose-900 flex items-center gap-1.5">
        <span>⚠️</span> System Notice
      </h3>
      <p className="text-xs text-rose-700 leading-relaxed">{message}</p>
    </div>
  );
}
