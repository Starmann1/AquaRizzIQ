interface Props {
  message?: string;
}

export default function ErrorDisplay({ message = 'An error occurred while loading data.' }: Props) {
  return (
    <div className="p-4 bg-red-900/20 border border-red-900/50 rounded-md text-red-400">
      <h3 className="font-semibold mb-1">Error</h3>
      <p className="text-sm">{message}</p>
    </div>
  );
}
