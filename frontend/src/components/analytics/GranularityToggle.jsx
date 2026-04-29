const GRANULARITIES = ['daily', 'weekly', 'monthly', 'annual']

export default function GranularityToggle({ value, onChange }) {
  return (
    <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
      {GRANULARITIES.map((g) => (
        <button
          key={g}
          type="button"
          onClick={() => onChange(g)}
          className={`px-3 py-1 rounded-md text-sm font-medium transition-colors capitalize ${
            value === g
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          {g}
        </button>
      ))}
    </div>
  )
}

export { GRANULARITIES }
