import { useEffect, useRef, useState } from 'react'

export function usePolling(fetchFn, intervalMs = 30000, reloadDeps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const fetchFnRef = useRef(fetchFn)
  fetchFnRef.current = fetchFn

  async function load() {
    try {
      const result = await fetchFnRef.current()
      setData(result)
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, intervalMs)
    return () => clearInterval(id)
  }, [intervalMs, ...reloadDeps])

  return { data, loading, error, reload: load }
}
