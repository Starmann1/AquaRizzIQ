export default function LoadingSpinner() {
  return (
    <div className="flex justify-center items-center p-6">
      <div className="animate-spin rounded-full h-8 w-8 border-3 border-sky-600 border-t-transparent shadow-xs"></div>
      <span className="ml-3 text-sm font-semibold text-sky-900">Loading data…</span>
    </div>
  );
}
