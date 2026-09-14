import { useApiHealth } from '../../hooks/useApiHealth'

export function ApiStatus() {
  const { state, retry } = useApiHealth()

  return (
    <div className="rounded-2xl border border-white/20 bg-black/10 px-4 py-3 text-sm text-white">
      <p role="status" className="flex items-center gap-2 font-medium">
        <span
          aria-hidden="true"
          className={`size-2 shrink-0 rounded-full ${state.status === 'connected' ? 'bg-emerald-300' : state.status === 'checking' ? 'bg-white/70' : 'bg-amber-300'}`}
        />
        {state.status === 'connected'
          ? 'Local API connected'
          : state.status === 'checking'
            ? 'Checking local API…'
            : 'Local API unavailable'}
      </p>
      {state.status === 'unavailable' && (
        <>
          <p className="mt-2 text-xs leading-relaxed text-white/85">{state.message}</p>
          <button
            type="button"
            onClick={retry}
            className="mt-2 min-h-11 rounded-md px-1 text-xs font-semibold underline decoration-white/50 underline-offset-4 hover:decoration-white focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white"
          >
            Retry connection
          </button>
        </>
      )}
      {state.status === 'connected' && (
        <p className="mt-1 text-xs leading-relaxed text-white/75">Service connection only</p>
      )}
    </div>
  )
}
