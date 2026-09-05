import { useEffect, useState } from 'react'
import { getAgentSettings, updateAgentSettings } from '../../api/businessApi'
import { useBusiness } from '../../context/BusinessContext'
import { Button, Card, ErrorBanner, Input, Skeleton, TextArea } from '../../components/business/Primitives'

const CHANNELS = [
  { name: 'send_whatsapp_message', label: 'WhatsApp' },
  { name: 'send_sms', label: 'SMS' },
  { name: 'send_email', label: 'Email' },
  { name: 'make_call', label: 'Voice call' },
  { name: 'send_app_notification', label: 'App notification' },
  { name: 'send_payment_link', label: 'Payment link' },
]

export default function Settings() {
  const { businessId } = useBusiness()
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getAgentSettings(businessId)
      .then((data) =>
        setForm({
          tone: data.tone || '',
          businessDescription: data.businessDescription || '',
          customInstructions: data.customInstructions || '',
          // `null` (unset) means "all channels enabled" - represent that as
          // every channel checked in the form.
          enabledChannels: data.enabledChannels ?? CHANNELS.map((c) => c.name),
        }),
      )
      .catch((reason) => setError(reason.message))
  }, [businessId])

  const toggleChannel = (name) => {
    setForm((prev) => ({
      ...prev,
      enabledChannels: prev.enabledChannels.includes(name)
        ? prev.enabledChannels.filter((c) => c !== name)
        : [...prev.enabledChannels, name],
    }))
  }

  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setError('')
    setSaved(false)
    try {
      await updateAgentSettings(businessId, form)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (reason) {
      setError(reason.message)
    } finally {
      setSaving(false)
    }
  }

  if (!form) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-96" />
      </div>
    )
  }

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Agent settings</h1>
        <p className="text-sm text-slate-400">
          Customize how your recovery agent talks to customers - this changes its actual behaviour,
          not just what's shown here.
        </p>
      </div>

      <form onSubmit={submit} className="flex flex-col gap-5">
        <Card className="flex flex-col gap-4">
          <Input
            label="Tone"
            value={form.tone}
            onChange={(e) => setForm({ ...form, tone: e.target.value })}
            placeholder="friendly and professional"
          />
          <TextArea
            label="About this business"
            rows={3}
            value={form.businessDescription}
            onChange={(e) => setForm({ ...form, businessDescription: e.target.value })}
            placeholder="We sell premium hand-roasted coffee subscriptions."
          />
          <TextArea
            label="Custom instructions"
            rows={4}
            value={form.customInstructions}
            onChange={(e) => setForm({ ...form, customInstructions: e.target.value })}
            placeholder="Always mention our 10% loyalty discount for repeat customers."
          />
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-bold text-slate-700">Enabled channels</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {CHANNELS.map((channel) => (
              <label
                key={channel.name}
                className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm transition-colors hover:bg-slate-50"
              >
                <input
                  type="checkbox"
                  checked={form.enabledChannels.includes(channel.name)}
                  onChange={() => toggleChannel(channel.name)}
                  className="h-4 w-4 accent-slate-900"
                />
                {channel.label}
              </label>
            ))}
          </div>
        </Card>

        <ErrorBanner message={error} />

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={saving}>
            {saving ? 'Saving…' : 'Save settings'}
          </Button>
          {saved && <span className="animate-fade-in text-sm font-semibold text-emerald-600">Saved ✓</span>}
        </div>
      </form>
    </div>
  )
}
