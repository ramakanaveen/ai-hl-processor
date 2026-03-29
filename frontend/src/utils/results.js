export function normalizeHeadline(headline = '') {
  return headline.trim().toLowerCase()
}

export function mergeResultWithOverride(result, overrides = {}) {
  const data = result?.data ?? result
  if (!data?.headline) return data

  const override = overrides[normalizeHeadline(data.headline)]
  return override ? { ...data, ...override } : data
}
