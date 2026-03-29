import { useState } from 'react'
import { api } from '../../api/client'

const ALL_CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD', 'CNY']
const DEFAULT_REASONING = 'Manual correction added by user'
const MIN_REASONING_LENGTH = 10

function EntityEditor({ entity, onChange, onRemove }) {
  const ccy = entity.currency?.value ?? entity.currency
  return (
    <div className="entity-row">
      <span className="entity-ccy">{ccy}</span>
      <input
        type="range"
        min={0} max={1} step={0.01}
        value={entity.confidence}
        onChange={e => onChange({ ...entity, confidence: parseFloat(e.target.value) })}
      />
      <span className="conf-pct">{Math.round(entity.confidence * 100)}%</span>
      <input
        type="text"
        className="reasoning-input"
        value={entity.reasoning}
        placeholder="Reasoning…"
        onChange={e => onChange({ ...entity, reasoning: e.target.value })}
      />
      <button className="btn-remove" onClick={onRemove}>✕</button>
    </div>
  )
}

export function CorrectionModal({ result, onClose, onSaved }) {
  const original = result?.impacted_entities ?? []
  const [entities, setEntities] = useState(
    original.map(e => ({
      currency: e.currency?.value ?? e.currency,
      confidence: e.confidence,
      reasoning: e.reasoning,
    }))
  )
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState(null)
  const [addCcy, setAddCcy] = useState(ALL_CURRENCIES[0])

  function updateEntity(i, updated) {
    setEntities(entities.map((e, idx) => idx === i ? updated : e))
  }

  function removeEntity(i) {
    setEntities(entities.filter((_, idx) => idx !== i))
  }

  function addEntity() {
    if (entities.find(e => (e.currency?.value ?? e.currency) === addCcy)) return
    setEntities([...entities, {
      currency: addCcy,
      confidence: 0.7,
      reasoning: DEFAULT_REASONING,
    }])
  }

  async function handleSave() {
    const invalid = entities.find(
      entity => !entity.reasoning || entity.reasoning.trim().length < MIN_REASONING_LENGTH
    )
    if (invalid) {
      setError(`Reasoning for ${invalid.currency} must be at least ${MIN_REASONING_LENGTH} characters.`)
      return
    }

    setSaving(true)
    setError(null)
    try {
      const response = await api.postCorrection({
        headline: result.headline,
        original_entities: original,
        corrected_entities: entities,
        correction_note: note,
        corrected_by: 'user',
      })
      if (response?.result) onSaved?.(response.result)
      setSaved(true)
      setTimeout(onClose, 1500)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h3>Adjust Analysis</h3>
          <button className="btn-close" onClick={onClose}>✕</button>
        </div>

        <p className="modal-headline">"{result.headline}"</p>

        <h4>Currency Impacts</h4>
        <div className="entity-list">
          {entities.map((e, i) => (
            <EntityEditor
              key={i}
              entity={e}
              onChange={updated => updateEntity(i, updated)}
              onRemove={() => removeEntity(i)}
            />
          ))}
        </div>

        <div className="add-currency">
          <select value={addCcy} onChange={e => setAddCcy(e.target.value)}>
            {ALL_CURRENCIES.map(c => <option key={c}>{c}</option>)}
          </select>
          <button onClick={addEntity}>+ Add currency</button>
        </div>

        <textarea
          className="correction-note"
          placeholder="Optional note about why you're correcting this…"
          value={note}
          onChange={e => setNote(e.target.value)}
          rows={2}
        />

        {error && <p className="error-msg">{error}</p>}
        {saved && <p className="success-msg">Saved!</p>}

        <div className="modal-footer">
          <button className="btn-cancel" onClick={onClose}>Cancel</button>
          <button className="btn-save" disabled={saving || saved} onClick={handleSave}>
            {saving ? 'Saving…' : 'Save adjustment'}
          </button>
        </div>
      </div>
    </div>
  )
}
