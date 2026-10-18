export function fmtDuration(hours) {
  const total = Math.round(hours * 60)
  const h = Math.floor(total / 60)
  const m = total % 60
  return h ? `${h}h ${String(m).padStart(2, '0')}m` : `${m}m`
}

export function fmtDateTime(isoOrDate) {
  return new Date(isoOrDate).toLocaleString([], {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

/** Value for <input type="datetime-local">: next full hour, in local time. */
export function defaultDeparture() {
  const d = new Date(Date.now() + 3600e3)
  d.setMinutes(0, 0, 0)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}
