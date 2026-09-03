import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import {
  getUserDashboard,
  sendDashboardMessage,
} from './demoApi'
import {
  agentJsonOutput,
  agentState,
  channelColor,
  formatDate,
  icons,
  labels,
  paymentSummary,
} from './dashboardUtils'
import {
  Message,
  Metric,
  StatusDot,
} from './components/Primitives'
import './App.css'

// ─── Sub-components ──────────────────────────────────────────────────────────

function AgentThinking({ reason }) {
  const [dots, setDots] = useState('.')

  useEffect(() => {
    const t = setInterval(() => {
      setDots((d) =>
        d.length >= 3 ? '.' : d + '.'
      )
    }, 500)

    return () => clearInterval(t)
  }, [])

  return (
    <div
      style={{
        display: 'flex',
        gap: 10,
        padding: '12px 14px',
        background:
          'linear-gradient(135deg, #0f2027 0%, #1a3a4a 100%)',
        borderRadius: 10,
        border: '1px solid #1e4d5e',
        marginBottom: 10,
      }}
    >
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: '50%',
          background: '#0e7a5a',
          display: 'grid',
          placeItems: 'center',
          fontSize: 13,
          flexShrink: 0,
        }}
      >
        🤖
      </div>

      <div>
        <div
          style={{
            fontSize: 10,
            color: '#4ade80',
            fontFamily: 'DM Mono',
            marginBottom: 3,
          }}
        >
          Agent reasoning{dots}
        </div>

        <div
          style={{
            fontSize: 11,
            color: '#94d3b8',
            lineHeight: 1.55,
          }}
        >
          {reason ||
            'Analyzing case context and determining optimal outreach strategy'}
        </div>
      </div>
    </div>
  )
}

function PhonePreview({
  message,
  customerResponse,
  channel,
  customerName,
  onDismiss,
  reply,
  onReplyChange,
  onReply,
  sending,
}) {
  const bgMap = {
    whatsapp: '#0a1628',
    sms: '#1c1c1e',
    email: '#1a1a2e',
  }

  const accentMap = {
    whatsapp: '#25D366',
    sms: '#007AFF',
    email: '#7c3aed',
  }

  const headerMap = {
    whatsapp: 'WhatsApp',
    sms: 'Messages',
    email: 'Mail',
  }

  const bg = bgMap[channel] || '#0a1628'
  const accent = accentMap[channel] || '#25D366'

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        maxWidth: 280,
        margin: '0 auto',
      }}
    >
      {/* Phone shell */}
      <div
        style={{
          background: '#1a1a1a',
          borderRadius: 36,
          padding: '12px 8px',
          boxShadow:
            '0 0 0 2px #333, 0 25px 60px #00000088, inset 0 0 0 1px #444',
          position: 'relative',
        }}
      >
        {/* Notch */}
        <div
          style={{
            width: 90,
            height: 22,
            background: '#1a1a1a',
            borderRadius: 12,
            margin: '0 auto 6px',
            position: 'relative',
            zIndex: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}
        >
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: '#2a2a2a',
              border: '1.5px solid #333',
            }}
          />
          <div
            style={{
              width: 46,
              height: 4,
              borderRadius: 3,
              background: '#2a2a2a',
            }}
          />
        </div>

        {/* Screen */}
        <div
          style={{
            background: bg,
            borderRadius: 26,
            overflow: 'hidden',
            minHeight: 320,
          }}
        >
          {/* Status bar */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '8px 16px 4px',
              fontSize: 10,
              color: '#fff',
              fontWeight: 700,
            }}
          >
            <span>9:41</span>
            <span>●●●</span>
          </div>

          {/* App header */}
          <div
            style={{
              background: bg,
              padding: '8px 14px 10px',
              borderBottom: `1px solid ${accent}22`,
            }}
          >
            <div
              style={{
                color: accent,
                fontSize: 11,
                fontWeight: 700,
                marginBottom: 2,
              }}
            >
              {headerMap[channel]}
            </div>

            <div
              style={{
                fontSize: 13,
                fontWeight: 800,
                color: '#fff',
              }}
            >
              {customerName || 'Recovery Agent'}
            </div>
          </div>

          {/* Message bubble */}
          <div style={{ padding: '14px 12px' }}>
            <div
              style={{
                background:
                  channel === 'email'
                    ? '#2d1b69'
                    : `${accent}22`,
                border: `1px solid ${accent}44`,
                borderRadius: '4px 14px 14px 14px',
                padding: '10px 12px',
                fontSize: 11,
                color: '#e2e8f0',
                lineHeight: 1.6,
                maxWidth: '85%',
              }}
            >
              {message ||
                'Your account requires attention. Please contact us to resolve your outstanding balance.'}

              <div
                style={{
                  color: `${accent}aa`,
                  fontSize: 9,
                  marginTop: 6,
                  textAlign: 'right',
                  fontFamily: 'DM Mono',
                }}
              >
                Delivered ·{' '}
                {new Date().toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>

            {customerResponse && (
              <div
                style={{
                  marginTop: 10,
                  marginLeft: '15%',
                  background: `${accent}cc`,
                  border: `1px solid ${accent}`,
                  borderRadius: '14px 4px 14px 14px',
                  padding: '10px 12px',
                  fontSize: 11,
                  color: '#fff',
                  lineHeight: 1.6,
                }}
              >
                {customerResponse}
                <div
                  style={{
                    color: '#ffffffaa',
                    fontSize: 9,
                    marginTop: 6,
                    textAlign: 'right',
                    fontFamily: 'DM Mono',
                  }}
                >
                  Sent ·{' '}
                  {new Date().toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Reply area */}
          <form
            onSubmit={onReply}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 12px',
              margin: '8px 12px',
              background: '#ffffff11',
              borderRadius: 20,
              border: '1px solid #ffffff15',
            }}
          >
            <input
              value={reply}
              onChange={(event) => onReplyChange(event.target.value)}
              placeholder="Reply to the agent..."
              aria-label={`Reply by ${channel}`}
              style={{
                flex: 1,
                minWidth: 0,
                border: 'none',
                outline: 'none',
                background: 'transparent',
                color: '#fff',
                fontSize: 10,
              }}
            />

            <button
              type="submit"
              disabled={sending || !reply.trim()}
              style={{
                width: 24,
                height: 24,
                border: 'none',
                borderRadius: '50%',
                background: sending ? '#64748b' : accent,
                color: '#fff',
                display: 'grid',
                placeItems: 'center',
                fontSize: 12,
                cursor: sending ? 'wait' : 'pointer',
              }}
            >
              ↑
            </button>
          </form>
        </div>

        {/* Home indicator */}
        <div
          style={{
            width: 100,
            height: 4,
            background: '#444',
            borderRadius: 3,
            margin: '8px auto 0',
          }}
        />
      </div>

      {onDismiss && (
        <button
          onClick={onDismiss}
          style={{
            position: 'absolute',
            top: -8,
            right: -8,
            width: 24,
            height: 24,
            borderRadius: '50%',
            background: '#ef4444',
            border: 'none',
            color: '#fff',
            fontSize: 14,
            fontWeight: 700,
            cursor: 'pointer',
            lineHeight: 1,
          }}
        >
          ×
        </button>
      )}
    </div>
  )
}

// ─── Main App ─────────────────────────────────────────────────────────────────

export default function App() {
  const [userId, setUserId] = useState(
    () =>
      localStorage.getItem(
        'recovery-demo-user'
      ) || ''
  )

  const [draft, setDraft] = useState(userId)
  const [channel, setChannel] = useState('whatsapp')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [showCallLog, setShowCallLog] =
    useState(false)
  const [activeCall, setActiveCall] =
    useState(null)
  const [showRaw, setShowRaw] = useState(false)
  const [reply, setReply] = useState('')
  const [sending, setSending] = useState(false)

  const knownMessageIds = useRef(new Set())

  useEffect(() => {
    if (!activeCall) return undefined

    const AudioContextClass =
      window.AudioContext || window.webkitAudioContext
    if (!AudioContextClass) return undefined

    const audio = new AudioContextClass()
    let stopped = false

    const tone = () => {
      if (stopped) return
      const start = audio.currentTime
      const oscillator = audio.createOscillator()
      const gain = audio.createGain()
      oscillator.type = 'sine'
      oscillator.frequency.setValueAtTime(520, start)
      oscillator.frequency.linearRampToValueAtTime(680, start + 0.18)
      gain.gain.setValueAtTime(0.0001, start)
      gain.gain.exponentialRampToValueAtTime(0.08, start + 0.03)
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.42)
      oscillator.connect(gain).connect(audio.destination)
      oscillator.start(start)
      oscillator.stop(start + 0.45)
    }

    void audio.resume().then(() => {
      tone()
    })
    const ringtone = window.setInterval(tone, 1800)

    return () => {
      stopped = true
      window.clearInterval(ringtone)
      void audio.close()
    }
  }, [activeCall])

  const announceNewMessages = useCallback(
    (incoming) => {
      const newItems = incoming.filter(
        (item) =>
          !knownMessageIds.current.has(
            item.event_id
          )
      )

      incoming.forEach((item) =>
        knownMessageIds.current.add(
          item.event_id
        )
      )

      if (!newItems.length) return

      const latest = newItems[0]

      setNotice(
        `${latest.channel}: ${latest.message.slice(
          0,
          80
        )}`
      )

      window.setTimeout(
        () => setNotice(''),
        6000
      )

      if (latest.channel === 'call') {
        setActiveCall(latest)
      }

      if (latest.channel !== 'call') try {
        const AudioContextClass =
          window.AudioContext ||
          window.webkitAudioContext

        if (!AudioContextClass) return

        const audio = new AudioContextClass()
        const osc = audio.createOscillator()
        const gain = audio.createGain()

        osc.frequency.value = 880

        gain.gain.setValueAtTime(
          0.045,
          audio.currentTime
        )

        osc.connect(gain).connect(
          audio.destination
        )

        osc.start()
        osc.stop(audio.currentTime + 0.17)

        setTimeout(
          () => audio.close(),
          350
        )
      } catch {
        // Optional audio notification.
      }
    },
    []
  )

  const refreshDashboard = useCallback(
    async (alertOnNew = false) => {
      if (!userId) return

      setLoading(true)
      setError('')

      try {
        const dashboard =
          await getUserDashboard(userId)

        const messages =
          dashboard?.recovery_case
            ?.communications || []

        if (
          knownMessageIds.current.size === 0
        ) {
          messages.forEach((item) =>
            knownMessageIds.current.add(
              item.event_id
            )
          )
        } else if (alertOnNew) {
          announceNewMessages(messages)
        }

        setData(dashboard)
      } catch (reason) {
        setData(null)

        setError(
          reason instanceof Error
            ? reason.message
            : 'Could not load dashboard.'
        )
      } finally {
        setLoading(false)
      }
    },
    [announceNewMessages, userId]
  )

  useEffect(() => {
    const t = setTimeout(
      () => refreshDashboard(false),
      0
    )

    return () => clearTimeout(t)
  }, [refreshDashboard])

  useEffect(() => {
    const t = setInterval(
      () => refreshDashboard(true),
      15000
    )

    return () => clearInterval(t)
  }, [refreshDashboard])

  const changeUser = () => {
    const id = draft.trim()

    if (!id) return

    localStorage.setItem(
      'recovery-demo-user',
      id
    )

    knownMessageIds.current = new Set()
    setData(null)
    setUserId(id)
  }

  const caseData = data?.recovery_case ?? null

  const communications = useMemo(
    () => caseData?.communications ?? [],
    [caseData]
  )

  const channelMessages = useMemo(
    () =>
      communications.filter(
        (item) =>
          item.channel === channel
      ),
    [communications, channel]
  )

  const callMessages = useMemo(
    () =>
      communications.filter(
        (item) =>
          item.channel === 'call'
      ),
    [communications]
  )

  const latestMessage =
    channelMessages[0] || null

  const submitReply = async (event) => {
    event.preventDefault()
    if (!caseData || !reply.trim() || sending) return

    setSending(true)
    setError('')
    try {
      await sendDashboardMessage(userId, {
        case_id: caseData.case_id,
        channel,
        message: reply.trim(),
      })
      setReply('')
      await refreshDashboard(false)
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : 'Could not send reply.'
      )
    } finally {
      setSending(false)
    }
  }

  return (
    <div style={styles.shell}>
      {/* ── Top bar ── */}
      <header style={styles.topbar}>
        <div style={styles.brand}>
          <span style={styles.brandMark}>
            R
          </span>

          <span
            style={{
              fontWeight: 800,
              fontSize: 15,
              letterSpacing: '-0.5px',
            }}
          >
            Recovery
          </span>

          <span style={styles.brandBadge}>
            AGENT DEMO
          </span>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 16,
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                background: '#22c55e',
                boxShadow:
                  '0 0 0 4px #22c55e33',
                display: 'inline-block',
              }}
            />

            <span
              style={{
                fontSize: 11,
                color: '#64748b',
                fontFamily: 'DM Mono',
              }}
            >
              Live · {communications.length}{' '}
              events
            </span>
          </div>

          <button
            onClick={() =>
              refreshDashboard(true)
            }
            disabled={loading}
            style={styles.refreshBtn}
          >
            {loading ? '…' : '↻'} Refresh
          </button>
        </div>
      </header>

      {/* ── Toast ── */}
      {notice && (
        <div style={styles.toast}>
          <span style={{ fontSize: 14 }}>
            ✦
          </span>

          <span
            style={{
              flex: 1,
              fontSize: 11,
              color: '#1e3a2f',
            }}
          >
            <b
              style={{
                display: 'block',
                marginBottom: 2,
              }}
            >
              New activity
            </b>

            {notice}
          </span>

          <button
            onClick={() => setNotice('')}
            style={{
              border: 'none',
              background: 'none',
              color: '#64748b',
              fontSize: 18,
              cursor: 'pointer',
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* ── Main workspace ── */}
      <div
        className="workspace-override"
        style={styles.workspace}
      >
        {/* ══ LEFT ══ */}
        <aside style={styles.leftPanel}>
          <div style={{ marginBottom: 20 }}>
            <div style={styles.eyebrow}>
              Customer lookup
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault()
                changeUser()
              }}
              style={styles.userForm}
            >
              <input
                value={draft}
                onChange={(e) =>
                  setDraft(e.target.value)
                }
                placeholder="Enter customer_id…"
                style={styles.userInput}
              />

              <button
                type="submit"
                style={styles.userBtn}
              >
                Load
              </button>
            </form>
          </div>

          {/* Customer card */}
          {caseData ? (
            <div style={styles.customerCard}>
              <div
                style={{
                  display: 'flex',
                  gap: 10,
                  alignItems: 'center',
                  marginBottom: 12,
                }}
              >
                <div style={styles.avatar}>
                  {(
                    caseData.customer_id ||
                    userId
                  )
                    .slice(0, 2)
                    .toUpperCase() || '—'}
                </div>

                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontWeight: 700,
                      fontSize: 13,
                      color: '#0f2027',
                    }}
                  >
                    {caseData.customer_id ||
                      userId}
                  </div>

                  <div
                    style={{
                      fontSize: 10,
                      color: '#64748b',
                      fontFamily: 'DM Mono',
                      marginTop: 2,
                    }}
                  >
                    {caseData.payment_id}
                  </div>
                </div>

                <span
                  style={{
                    padding: '4px 9px',
                    borderRadius: 20,
                    background:
                      caseData.status ===
                      'active'
                        ? '#dcfce7'
                        : caseData.status ===
                          'processing'
                        ? '#fef3c7'
                        : '#fee2e2',
                    color:
                      caseData.status ===
                      'active'
                        ? '#166534'
                        : caseData.status ===
                          'processing'
                        ? '#92400e'
                        : '#991b1b',
                    fontSize: 9,
                    fontWeight: 700,
                    fontFamily: 'DM Mono',
                    textTransform:
                      'uppercase',
                  }}
                >
                  {caseData.status}
                </span>
              </div>

              <div style={styles.alertBar}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    background: '#fff0d8',
                    display: 'grid',
                    placeItems: 'center',
                    fontSize: 16,
                    flexShrink: 0,
                  }}
                >
                  ⚠️
                </div>

                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: '#92400e',
                      textTransform:
                        'capitalize',
                    }}
                  >
                    {String(
                      caseData.trigger_type ||
                        'unknown'
                    ).replaceAll(
                      '_',
                      ' '
                    )}
                  </div>

                  <div
                    style={{
                      fontSize: 10,
                      color: '#b45309',
                      marginTop: 2,
                    }}
                  >
                    {paymentSummary(caseData)}
                  </div>
                </div>

                <div
                  style={{
                    fontSize: 9,
                    fontFamily: 'DM Mono',
                    color: '#d97706',
                    fontWeight: 700,
                  }}
                >
                  {caseData.attempt_count}×
                  attempts
                </div>
              </div>
            </div>
          ) : (
            <div
              style={{
                padding: '20px 16px',
                borderRadius: 12,
                border:
                  '1.5px dashed #cbd5e1',
                textAlign: 'center',
                color: '#94a3b8',
                fontSize: 12,
              }}
            >
              Enter a customer ID to load their
              recovery case
            </div>
          )}

          {error && (
            <div
              style={{
                marginTop: 12,
                padding: '10px 12px',
                borderRadius: 8,
                background: '#fef2f2',
                color: '#dc2626',
                fontSize: 11,
                lineHeight: 1.5,
                border:
                  '1px solid #fecaca',
              }}
            >
              {error}
            </div>
          )}

          {/* Channel tabs */}
          <div style={{ marginTop: 20 }}>
            <div style={styles.eyebrow}>
              Outreach channel
            </div>

            <div style={styles.channelTabs}>
              {Object.keys(icons).map((ch) => {
                const count =
                  communications.filter(
                    (item) =>
                      item.channel === ch
                  ).length

                return (
                  <button
                    key={ch}
                    onClick={() =>
                      setChannel(ch)
                    }
                    style={{
                      ...styles.channelTab,
                      background:
                        channel === ch
                          ? channelColor[ch]
                          : 'transparent',
                      color:
                        channel === ch
                          ? '#fff'
                          : '#64748b',
                      boxShadow:
                        channel === ch
                          ? `0 4px 12px ${channelColor[ch]}44`
                          : 'none',
                    }}
                  >
                    <span
                      style={{ fontSize: 14 }}
                    >
                      {icons[ch]}
                    </span>

                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                      }}
                    >
                      {labels[ch]}
                    </span>

                    <span
                      style={{
                        marginLeft: 'auto',
                        fontSize: 9,
                        fontFamily:
                          'DM Mono',
                        background:
                          channel === ch
                            ? '#ffffff33'
                            : '#e2e8f0',
                        color:
                          channel === ch
                            ? '#fff'
                            : '#475569',
                        padding:
                          '1px 6px',
                        borderRadius: 10,
                      }}
                    >
                      {count}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Message list */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
              marginTop: 12,
              paddingRight: 2,
            }}
          >
            {loading && (
              <div
                style={{
                  textAlign: 'center',
                  color: '#94a3b8',
                  fontSize: 11,
                  padding: 20,
                }}
              >
                Loading…
              </div>
            )}

            {!loading &&
              !channelMessages.length && (
                <div
                  style={{
                    textAlign:
                      'center',
                    color: '#94a3b8',
                    fontSize: 11,
                    padding: 24,
                    lineHeight: 1.6,
                  }}
                >
                  No {labels[channel]}{' '}
                  messages for this case
                  yet.
                </div>
              )}

            {channelMessages.map(
              (msg) => (
                <Message
                  key={msg.event_id}
                  item={msg}
                />
              )
            )}
          </div>

          {/* Call log */}
          {callMessages.length > 0 && (
            <div
              style={{ marginTop: 12 }}
            >
              <button
                onClick={() =>
                  setShowCallLog(
                    !showCallLog
                  )
                }
                style={styles.callLogBtn}
              >
                <span
                  style={{
                    display: 'flex',
                    alignItems:
                      'center',
                    gap: 6,
                  }}
                >
                  <span
                    style={{
                      width: 22,
                      height: 22,
                      borderRadius: 6,
                      background:
                        '#e0f2fe',
                      display: 'grid',
                      placeItems:
                        'center',
                      fontSize: 12,
                      color:
                        '#0284c7',
                    }}
                  >
                    📞
                  </span>

                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                    }}
                  >
                    Calls
                  </span>

                  <span
                    style={{
                      fontSize: 9,
                      fontFamily:
                        'DM Mono',
                      background:
                        '#e0f2fe',
                      color:
                        '#0284c7',
                      padding:
                        '1px 6px',
                      borderRadius:
                        10,
                    }}
                  >
                    {callMessages.length}
                  </span>
                </span>

                <span
                  style={{
                    fontSize: 16,
                    color: '#94a3b8',
                  }}
                >
                  {showCallLog
                    ? '⌃'
                    : '⌄'}
                </span>
              </button>

              {showCallLog && (
                <div
                  style={{
                    borderTop:
                      '1px solid #e2e8f0',
                  }}
                >
                  {callMessages.map(
                    (item) => (
                      <button
                        key={
                          item.event_id
                        }
                        onClick={() =>
                          setActiveCall(
                            item
                          )
                        }
                        style={
                          styles.callRow
                        }
                      >
                        <div>
                          <div
                            style={{
                              fontSize: 10,
                              fontWeight:
                                700,
                              textTransform:
                                'capitalize',
                            }}
                          >
                            {
                              item.status
                            }
                          </div>

                          <div
                            style={{
                              fontSize: 9,
                              color:
                                '#94a3b8',
                              fontFamily:
                                'DM Mono',
                              marginTop: 2,
                            }}
                          >
                            {formatDate(
                              item.created_at
                            )}
                          </div>
                        </div>

                        <span
                          style={{
                            fontSize: 10,
                            color:
                              '#0284c7',
                            fontWeight:
                              700,
                          }}
                        >
                          View →
                        </span>
                      </button>
                    )
                  )}
                </div>
              )}
            </div>
          )}
        </aside>

        {/* ══ CENTER ══ */}
        <section
          style={styles.centerPanel}
        >
          <div
            style={{
              textAlign: 'center',
              marginBottom: 6,
            }}
          >
            <div style={styles.eyebrow}>
              What the customer
              receives
            </div>

            <h2
              style={{
                margin:
                  '4px 0 0',
                fontSize: 17,
                fontWeight: 800,
                color: '#0f2027',
                letterSpacing:
                  '-0.5px',
              }}
            >
              Live message preview
            </h2>
          </div>

          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection:
                'column',
              alignItems:
                'center',
              justifyContent:
                'center',
              gap: 20,
            }}
          >
            <PhonePreview
              message={
                latestMessage?.message
              }
              customerResponse={
                latestMessage?.customer_response
              }
              channel={channel}
              customerName={
                caseData?.customer_id ||
                userId
              }
              reply={reply}
              onReplyChange={setReply}
              onReply={submitReply}
              sending={sending}
            />

            {latestMessage && (
              <div
                style={{
                  display: 'flex',
                  flexDirection:
                    'column',
                  alignItems:
                    'center',
                  gap: 6,
                  padding:
                    '10px 16px',
                  background:
                    '#fff',
                  border:
                    '1px solid #e2e8f0',
                  borderRadius:
                    10,
                  width: '100%',
                  maxWidth: 280,
                }}
              >
                <div
                  style={{
                    display:
                      'flex',
                    gap: 8,
                    alignItems:
                      'center',
                  }}
                >
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius:
                        '50%',
                      background:
                        latestMessage.status ===
                        'delivered'
                          ? '#22c55e'
                          : '#f59e0b',
                    }}
                  />

                  <span
                    style={{
                      fontSize: 10,
                      fontWeight:
                        700,
                      color:
                        '#374151',
                    }}
                  >
                    {latestMessage.status ===
                    'delivered'
                      ? 'Delivered'
                      : latestMessage.status}
                  </span>
                </div>

                <div
                  style={{
                    fontSize: 9,
                    color:
                      '#94a3b8',
                    fontFamily:
                      'DM Mono',
                  }}
                >
                  {formatDate(
                    latestMessage.created_at
                  )}
                </div>
              </div>
            )}

            {!caseData &&
              !loading && (
                <div
                  style={{
                    textAlign:
                      'center',
                    color:
                      '#94a3b8',
                    fontSize: 12,
                    lineHeight: 1.7,
                    maxWidth: 220,
                  }}
                >
                  Load a customer to
                  see what messages
                  your agent sends
                  them in real time.
                </div>
              )}
          </div>
        </section>

        {/* ══ RIGHT ══ */}
        <section
          style={styles.rightPanel}
        >
          <div style={styles.eyebrow}>
            Agent state
          </div>

          <div
            style={styles.agentHeader}
          >
            <div
              style={{
                display: 'flex',
                alignItems:
                  'center',
                gap: 8,
              }}
            >
              <StatusDot
                status={
                  caseData?.status ||
                  'idle'
                }
              />

              <h2
                style={{
                  margin: 0,
                  fontSize: 18,
                  fontWeight: 800,
                  color: '#fff',
                  letterSpacing:
                    '-0.5px',
                  textTransform:
                    'capitalize',
                }}
              >
                {agentState(
                  caseData
                )}
              </h2>
            </div>

            {caseData && (
              <span
                style={{
                  fontSize: 9,
                  fontFamily:
                    'DM Mono',
                  color:
                    '#64748b',
                }}
              >
                {caseData.case_id}
              </span>
            )}
          </div>

          {/* Metrics */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns:
                '1fr 1fr',
              gap: 8,
              marginBottom: 14,
            }}
          >
            <Metric
              value={String(
                data?.metrics
                  ?.handled_today ??
                  '—'
              )}
              label="Handled today"
              accent="#22c55e"
            />

            <Metric
              value={String(
                data?.metrics
                  ?.in_progress ??
                  '—'
              )}
              label="In progress"
              accent="#f59e0b"
            />

            <Metric
              value={String(
                data?.metrics
                  ?.queued_cases ??
                  '—'
              )}
              label="Queued"
              accent="#6366f1"
            />

            <Metric
              value={
                data
                  ? `${data.metrics.recovery_rate}%`
                  : '—'
              }
              label="Recovery rate"
              accent="#0ea5e9"
            />
          </div>

          {caseData?.decision_reason && (
            <AgentThinking
              reason={
                caseData.decision_reason
              }
            />
          )}

          {/* Decision card */}
          <div
            style={styles.decisionCard}
          >
            <div
              style={{
                fontSize: 10,
                color: '#4ade80',
                fontFamily:
                  'DM Mono',
                marginBottom:
                  10,
              }}
            >
              Decision snapshot
            </div>

            <div
              style={{
                display: 'flex',
                flexDirection:
                  'column',
                gap: 10,
              }}
            >
              <div
                style={
                  styles.decisionRow
                }
              >
                <span
                  style={
                    styles.decisionLabel
                  }
                >
                  Next action
                </span>

                <span
                  style={{
                    fontSize: 12,
                    fontWeight:
                      700,
                    color:
                      '#e2e8f0',
                    textTransform:
                      'capitalize',
                  }}
                >
                  {caseData?.next_action
                    ? caseData.next_action.replaceAll(
                        '_',
                        ' '
                      )
                    : 'Awaiting case'}
                </span>
              </div>

              <div
                style={
                  styles.decisionRow
                }
              >
                <span
                  style={
                    styles.decisionLabel
                  }
                >
                  Priority score
                </span>

                <span
                  style={{
                    fontSize: 12,
                    fontWeight:
                      700,
                    color:
                      '#fbbf24',
                  }}
                >
                  {caseData?.priority_score ??
                    '—'}
                </span>
              </div>

              <div
                style={
                  styles.decisionRow
                }
              >
                <span
                  style={
                    styles.decisionLabel
                  }
                >
                  Attempts made
                </span>

                <span
                  style={{
                    fontSize: 12,
                    fontWeight:
                      700,
                    color:
                      '#94a3b8',
                  }}
                >
                  {caseData?.attempt_count ??
                    '—'}
                </span>
              </div>

              <div
                style={
                  styles.decisionRow
                }
              >
                <span
                  style={
                    styles.decisionLabel
                  }
                >
                  Last channel
                </span>

                <span
                  style={{
                    fontSize: 12,
                    fontWeight:
                      700,
                    color:
                      '#94a3b8',
                    textTransform:
                      'capitalize',
                  }}
                >
                  {communications[0]
                    ?.channel ||
                    '—'}
                </span>
              </div>
            </div>
          </div>

          {/* Raw JSON */}
          <div style={{ marginTop: 12 }}>
            <button
              onClick={() =>
                setShowRaw(
                  !showRaw
                )
              }
              style={
                styles.rawToggle
              }
            >
              <span>⌘</span>

              <span
                style={{
                  flex: 1,
                  textAlign:
                    'left',
                }}
              >
                {showRaw
                  ? 'Hide'
                  : 'Inspect'}{' '}
                agent context
              </span>

              <span
                style={{
                  fontSize: 12,
                  color:
                    '#475569',
                }}
              >
                {showRaw
                  ? '⌃'
                  : '⌄'}
              </span>
            </button>

            {showRaw && (
              <div
                style={{
                  display: 'flex',
                  flexDirection:
                    'column',
                  gap: 8,
                  marginTop: 8,
                }}
              >
                <div
                  style={
                    styles.jsonBlock
                  }
                >
                  <div
                    style={{
                      fontSize: 9,
                      color:
                        '#4ade80',
                      fontFamily:
                        'DM Mono',
                      marginBottom:
                        8,
                    }}
                  >
                    context → agent
                  </div>

                  <pre
                    style={
                      styles.jsonPre
                    }
                  >
                    {JSON.stringify(
                      caseData?.context ??
                        {},
                      null,
                      2
                    )}
                  </pre>
                </div>

                <div
                  style={{
                    ...styles.jsonBlock,
                    background:
                      '#0f1f1a',
                  }}
                >
                  <div
                    style={{
                      fontSize: 9,
                      color:
                        '#34d399',
                      fontFamily:
                        'DM Mono',
                      marginBottom:
                        8,
                    }}
                  >
                    agent → output
                  </div>

                  <pre
                    style={
                      styles.jsonPre
                    }
                  >
                    {JSON.stringify(
                      agentJsonOutput(
                        caseData
                      ),
                      null,
                      2
                    )}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>

      {/* ── Call popup ── */}
      {activeCall && (
        <aside
          style={styles.callPopup}
        >
          <div
            style={
              {
                ...styles.callerAvatar,
                animation: 'callPulse 1.5s ease-in-out infinite',
              }
            }
          >
            {userId
              .slice(0, 2)
              .toUpperCase() ||
              '—'}
          </div>

          <div
            style={{
              fontSize: 9,
              color:
                '#94d3a2',
              fontFamily:
                'DM Mono',
              marginTop: 10,
            }}
          >
            {activeCall.status === 'delivered'
              ? 'Call connected'
              : 'Incoming call'}
          </div>

          <h3
            style={{
              margin:
                '5px 0 4px',
              fontSize: 17,
              fontWeight:
                800,
              color: '#fff',
            }}
          >
            {caseData?.customer_id ||
              userId}
          </h3>

          <p
            style={{
              margin: 0,
              fontSize: 10,
              color:
                '#94a3b8',
              lineHeight: 1.5,
              padding:
                '0 8px',
            }}
          >
            {activeCall.message}
          </p>

          <div
            style={{
              display: 'flex',
              gap: 12,
              justifyContent:
                'center',
              marginTop: 20,
            }}
          >
            <button
              onClick={() =>
                setActiveCall(
                  null
                )
              }
              style={{
                width: 46,
                height: 46,
                borderRadius:
                  '50%',
                border: 'none',
                background:
                  '#ef4444',
                color: '#fff',
                fontSize: 20,
                cursor:
                  'pointer',
              }}
            >
              ✕
            </button>

            <button
              onClick={() =>
                setActiveCall(
                  null
                )
              }
              style={{
                width: 46,
                height: 46,
                borderRadius:
                  '50%',
                border: 'none',
                background:
                  '#22c55e',
                color: '#fff',
                fontSize: 20,
                cursor:
                  'pointer',
                animation:
                  'ring 1.2s infinite',
              }}
            >
              ⌕
            </button>
          </div>
        </aside>
      )}
    </div>
  )
}

// ─── Style objects ────────────────────────────────────────────────────────────

const styles = {
  shell: {
    width: '100%',
    maxWidth: 'none',
    minHeight: '100vh',
    margin: '0 auto',
    background: '#f1f5f4',
    display: 'flex',
    flexDirection: 'column',
  },

  topbar: {
    height: 56,
    padding: '0 28px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    background: '#fff',
    borderBottom:
      '1px solid #e2e8e4',
    position: 'sticky',
    top: 0,
    zIndex: 10,
  },

  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },

  brandMark: {
    width: 28,
    height: 28,
    borderRadius: 8,
    background: '#0f2027',
    color: '#4ade80',
    display: 'grid',
    placeItems: 'center',
    fontFamily: 'Georgia',
    fontSize: 18,
    fontWeight: 700,
  },

  brandBadge: {
    fontSize: 8,
    fontFamily: 'DM Mono',
    fontWeight: 700,
    padding: '3px 6px',
    borderRadius: 4,
    background: '#dcfce7',
    color: '#166534',
    letterSpacing: '0.8px',
  },

  refreshBtn: {
    border:
      '1px solid #e2e8e4',
    borderRadius: 7,
    padding: '6px 12px',
    background: '#fff',
    color: '#374151',
    fontSize: 11,
    fontWeight: 700,
  },

  toast: {
    position: 'fixed',
    zIndex: 20,
    top: 64,
    right: 20,
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    width: 320,
    padding: '12px 14px',
    background: '#f0fdf4',
    border:
      '1px solid #bbf7d0',
    borderRadius: 10,
    boxShadow:
      '0 8px 24px #00000018',
  },

  workspace: {
    display: 'grid',
    gridTemplateColumns:
      '300px 1fr 320px',
    flex: 1,
    minHeight:
      'calc(100vh - 56px)',
  },

  leftPanel: {
    background: '#fff',
    borderRight:
      '1px solid #e2e8e4',
    padding: '24px 16px',
    display: 'flex',
    flexDirection:
      'column',
    gap: 0,
    overflowY: 'auto',
    maxHeight:
      'calc(100vh - 56px)',
  },

  centerPanel: {
    display: 'flex',
    flexDirection:
      'column',
    alignItems:
      'center',
    padding: '32px 24px',
    background:
      'linear-gradient(160deg, #e8f4ef 0%, #f0f7f4 60%, #e8eef4 100%)',
    overflowY: 'auto',
    maxHeight:
      'calc(100vh - 56px)',
  },

  rightPanel: {
    background: '#0f2027',
    borderLeft:
      '1px solid #1e3a4a',
    padding: '24px 18px',
    overflowY: 'auto',
    maxHeight:
      'calc(100vh - 56px)',
  },

  eyebrow: {
    fontSize: 9,
    fontFamily: 'DM Mono',
    fontWeight: 500,
    letterSpacing: '1.2px',
    color: '#94a3b8',
    textTransform:
      'uppercase',
    marginBottom: 8,
  },

  userForm: {
    display: 'flex',
    gap: 6,
    padding: '8px 10px',
    border:
      '1.5px solid #e2e8e4',
    borderRadius: 10,
    background: '#f8fafc',
    alignItems: 'center',
  },

  userInput: {
    flex: 1,
    border: 'none',
    outline: 'none',
    background:
      'transparent',
    fontSize: 12,
    color: '#0f2027',
    fontFamily: 'DM Mono',
  },

  userBtn: {
    border: 'none',
    borderRadius: 6,
    background: '#0f2027',
    color: '#4ade80',
    padding: '6px 12px',
    fontSize: 11,
    fontWeight: 700,
  },

  customerCard: {
    padding: 14,
    borderRadius: 12,
    background: '#fff',
    border:
      '1.5px solid #e2e8e4',
    marginBottom: 4,
  },

  avatar: {
    width: 36,
    height: 36,
    borderRadius: '50%',
    background: '#fde68a',
    color: '#78350f',
    display: 'grid',
    placeItems: 'center',
    fontSize: 11,
    fontWeight: 800,
    flexShrink: 0,
  },

  alertBar: {
    display: 'flex',
    gap: 8,
    alignItems: 'center',
    padding: 10,
    background: '#fffbeb',
    borderRadius: 8,
    border:
      '1px solid #fde68a',
  },

  channelTabs: {
    display: 'flex',
    flexDirection:
      'column',
    gap: 4,
  },

  channelTab: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '9px 12px',
    borderRadius: 8,
    border: 'none',
    transition:
      'all 0.2s',
    textAlign: 'left',
    width: '100%',
  },

  callLogBtn: {
    display: 'flex',
    width: '100%',
    alignItems: 'center',
    justifyContent:
      'space-between',
    padding: '10px 12px',
    border:
      '1px solid #e2e8e4',
    borderRadius: 8,
    background: '#fff',
    marginBottom: 0,
  },

  callRow: {
    display: 'flex',
    width: '100%',
    justifyContent:
      'space-between',
    alignItems: 'center',
    padding: '9px 12px',
    border: 'none',
    borderBottom:
      '1px solid #f1f5f9',
    background: '#fff',
    textAlign: 'left',
  },

  agentHeader: {
    display: 'flex',
    justifyContent:
      'space-between',
    alignItems:
      'flex-start',
    marginBottom: 16,
    paddingBottom: 14,
    borderBottom:
      '1px solid #1e3a4a',
  },

  decisionCard: {
    padding: '14px',
    borderRadius: 10,
    background:
      'linear-gradient(135deg, #0f2027, #1a3a4a)',
    border:
      '1px solid #1e4d5e',
  },

  decisionRow: {
    display: 'flex',
    justifyContent:
      'space-between',
    alignItems: 'center',
    paddingBottom: 8,
    borderBottom:
      '1px solid #1e3a4a',
  },

  decisionLabel: {
    fontSize: 9,
    fontFamily: 'DM Mono',
    color: '#64748b',
    textTransform:
      'uppercase',
  },

  rawToggle: {
    display: 'flex',
    width: '100%',
    alignItems: 'center',
    gap: 8,
    padding: '9px 12px',
    borderRadius: 8,
    border:
      '1px solid #1e3a4a',
    background: '#0a1a22',
    color: '#64748b',
    fontSize: 11,
    fontWeight: 600,
  },

  jsonBlock: {
    padding: 14,
    borderRadius: 8,
    border:
      '1px solid #1e3a4a',
    background: '#0a1628',
  },

  jsonPre: {
    margin: 0,
    color: '#7dd3b0',
    fontSize: 10,
    fontFamily: 'DM Mono',
    lineHeight: 1.6,
    whiteSpace: 'pre-wrap',
    maxHeight: 200,
    overflowY: 'auto',
  },

  callPopup: {
    position: 'fixed',
    zIndex: 30,
    right: 24,
    bottom: 24,
    width: 260,
    padding:
      '22px 18px 18px',
    background: '#0f2027',
    borderRadius: 20,
    textAlign: 'center',
    boxShadow:
      '0 20px 50px #00000055',
    border:
      '1px solid #1e4d5e',
  },

  callerAvatar: {
    width: 52,
    height: 52,
    borderRadius: '50%',
    background: '#fde68a',
    color: '#78350f',
    display: 'grid',
    placeItems: 'center',
    fontSize: 14,
    fontWeight: 800,
    margin: '0 auto',
    border:
      '3px solid #2a5568',
  },
}