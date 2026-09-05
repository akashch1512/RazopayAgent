import { formatTime } from '../dashboardUtils'

export function StatusDot({ status }) {
  const colors = {
    active: '#22c55e',
    processing: '#f59e0b',
    failed: '#ef4444',
    escalated: '#ef4444',
    idle: '#94a3b8',
  }

  const color = colors[status] || '#94a3b8'

  return (
    <span
      style={{
        display: 'inline-block',
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: color,
        boxShadow: `0 0 0 3px ${color}33`,
        flexShrink: 0,
        transition: 'background 0.3s ease, box-shadow 0.3s ease',
      }}
      className={status === 'processing' ? 'animate-pulse' : ''}
    />
  )
}

export function Message({ item }) {
  return (
    <div
      className="animate-fade-in-up"
      style={{
        alignSelf: 'flex-start',
        maxWidth: '80%',
        background: '#fff',
        borderRadius: '4px 12px 12px 12px',
        padding: '9px 11px',
        fontSize: 11,
        lineHeight: 1.6,
        boxShadow: '0 1px 3px #00000012',
        border: '1px solid #e8eeed',
      }}
    >
      {item.message}
      <div
        style={{
          fontSize: 9,
          color: '#94a3b8',
          marginTop: 4,
          display: 'flex',
          gap: 6,
          justifyContent: 'flex-end',
          fontFamily: 'DM Mono',
        }}
      >
        <span>{formatTime(item.created_at)}</span>
        <span
          style={{
            padding: '1px 5px',
            borderRadius: 3,
            background: item.status === 'delivered' ? '#dcfce7' : '#fef3c7',
            color: item.status === 'delivered' ? '#166534' : '#92400e',
          }}
        >
          {item.status}
        </span>
      </div>
      {item.customer_response && (
        <div
          className="animate-pop-in"
          style={{
            marginTop: 8,
            padding: '7px 9px',
            background: '#f0fdf4',
            borderRadius: '0 8px 8px 8px',
            fontSize: 10,
            color: '#166534',
            borderLeft: '2px solid #22c55e',
          }}
        >
          {item.customer_response}
        </div>
      )}
    </div>
  )
}

export function Metric({ value, label, accent }) {
  return (
    <article
      style={{
        padding: '14px 16px',
        borderRadius: 10,
        background: '#fff',
        border: '1px solid #e2e8e4',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
      }}
    >
      <strong
        style={{
          fontSize: 22,
          fontWeight: 800,
          letterSpacing: '-1px',
          color: accent || '#172329',
        }}
      >
        {value}
      </strong>
      <small
        style={{
          fontSize: 9,
          color: '#94a3b8',
          fontFamily: 'DM Mono',
        }}
      >
        {label}
      </small>
    </article>
  )
}
