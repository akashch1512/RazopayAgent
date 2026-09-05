import { useState } from 'react'

const TOOL_LABELS = {
  make_call: 'Placed a call',
  send_sms: 'Sent an SMS',
  send_whatsapp_message: 'Sent a WhatsApp message',
  send_app_notification: 'Sent an app notification',
  send_email: 'Sent an email',
  send_payment_link: 'Sent a payment link',
  track_payment_status: 'Checked payment status',
}

function formatTime(value) {
  if (!value) return ''
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function mergeEntries(history, actions) {
  const inbound = (history || []).map((event) => ({
    kind: 'inbound',
    id: `event-${event.id}`,
    timestamp: event.eventCreatedAt || event.receivedAt,
    title: event.eventType,
    subtitle: `${event.entityType || 'entity'}:${event.entityId || '—'} · status=${event.entityStatus || 'n/a'}`,
    raw: event,
  }))

  const outbound = (actions || []).map((action) => ({
    kind: 'outbound',
    id: `action-${action.id}`,
    timestamp: action.createdAt,
    title: TOOL_LABELS[action.toolName] || action.toolName,
    subtitle: action.status === 'success' ? 'Succeeded' : `Failed`,
    raw: action,
  }))

  return [...inbound, ...outbound].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
}

function DetailPanel({ entry }) {
  if (entry.kind === 'inbound') {
    const event = entry.raw
    return (
      <div className="space-y-2 text-xs">
        <Row label="Order / entity" value={event.orderId || event.entityId || '—'} />
        <Row label="Signature verified" value={event.signatureVerified ? 'Yes' : 'No'} />
        <div>
          <div className="mb-1 font-semibold text-slate-500">Raw payload</div>
          <pre className="max-h-56 overflow-auto rounded-lg bg-slate-900 p-3 text-[10px] leading-relaxed text-emerald-300">
            {JSON.stringify(event.payload, null, 2)}
          </pre>
        </div>
      </div>
    )
  }

  const action = entry.raw
  return (
    <div className="space-y-2 text-xs">
      <Row label="Tool" value={action.toolName} />
      <Row label="Status" value={action.status} />
      <div>
        <div className="mb-1 font-semibold text-slate-500">Sent (tool input)</div>
        <pre className="max-h-40 overflow-auto rounded-lg bg-slate-900 p-3 text-[10px] leading-relaxed text-sky-300">
          {JSON.stringify(action.toolInput, null, 2)}
        </pre>
      </div>
      {action.toolOutput && (
        <div>
          <div className="mb-1 font-semibold text-slate-500">Response</div>
          <p className="rounded-lg bg-emerald-50 p-3 text-[11px] leading-relaxed text-emerald-800">
            {action.toolOutput}
          </p>
        </div>
      )}
    </div>
  )
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="font-semibold text-slate-500">{label}</span>
      <span className="text-right text-slate-700">{value}</span>
    </div>
  )
}

export default function Timeline({ history, actions }) {
  const entries = mergeEntries(history, actions)
  const [openId, setOpenId] = useState(null)

  if (!entries.length) {
    return <p className="text-sm text-slate-400">No activity recorded for this case yet.</p>
  }

  return (
    <ol className="relative space-y-1 pl-6">
      <div className="absolute top-1 bottom-1 left-[7px] w-px bg-slate-200" />
      {entries.map((entry, index) => {
        const isOpen = openId === entry.id
        const dotColor = entry.kind === 'inbound' ? 'bg-sky-500' : 'bg-violet-500'

        return (
          <li key={entry.id} className="stagger-item relative" style={{ '--i': index }}>
            <span
              className={`absolute -left-6 top-1.5 h-3 w-3 rounded-full ring-4 ring-white ${dotColor}`}
            />
            <button
              type="button"
              onClick={() => setOpenId(isOpen ? null : entry.id)}
              className="flex w-full items-start justify-between gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-slate-50"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide ${
                      entry.kind === 'inbound' ? 'bg-sky-100 text-sky-700' : 'bg-violet-100 text-violet-700'
                    }`}
                  >
                    {entry.kind === 'inbound' ? 'Received' : 'Agent action'}
                  </span>
                  <span className="truncate text-sm font-semibold text-slate-800">{entry.title}</span>
                </div>
                <p className="mt-0.5 truncate text-xs text-slate-400">{entry.subtitle}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2 text-[11px] text-slate-400">
                {formatTime(entry.timestamp)}
                <span className={`transition-transform ${isOpen ? 'rotate-180' : ''}`}>⌄</span>
              </div>
            </button>
            {isOpen && (
              <div className="animate-fade-in-up ml-3 mb-2 rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                <DetailPanel entry={entry} />
              </div>
            )}
          </li>
        )
      })}
    </ol>
  )
}
