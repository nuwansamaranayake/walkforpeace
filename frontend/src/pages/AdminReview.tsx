import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle, XCircle, AlertTriangle, Loader2, Download } from 'lucide-react'
import { getApplication, reviewApplication, revokeCredential } from '../services/api'

export default function AdminReview() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [app, setApp] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [action, setAction] = useState<'approve' | 'reject' | null>(null)
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!id) return
    getApplication(id)
      .then(r => setApp(r.data))
      .catch(() => navigate('/admin/dashboard'))
      .finally(() => setLoading(false))
  }, [id])

  const handleReview = async () => {
    if (!action || !id) return
    setSubmitting(true)
    try {
      await reviewApplication(id, action, notes)
      // Refresh
      const { data } = await getApplication(id)
      setApp(data)
      setAction(null)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Action failed')
    } finally {
      setSubmitting(false)
    }
  }

  const handleRevoke = async () => {
    if (!id || !confirm('Revoke this credential? This cannot be undone.')) return
    try {
      await revokeCredential(id)
      const { data } = await getApplication(id)
      setApp(data)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Revocation failed')
    }
  }

  if (loading) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-saffron" /></div>
  if (!app) return null

  const matchPct = app.face_match_score !== null ? (app.face_match_score * 100).toFixed(1) : null

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-navy text-white px-6 py-4">
        <Link to="/admin/dashboard" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-1">
          <ArrowLeft className="w-4 h-4" /> Back to dashboard
        </Link>
        <h1 className="text-lg font-bold text-saffron">Review Application — {app.ref_number}</h1>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left: Photos */}
          <div className="lg:col-span-2 space-y-4">
            {/* Face comparison */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-navy">Face Verification</h2>
                {matchPct && (
                  <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${
                    app.face_match_flagged ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                  }`}>
                    {app.face_match_flagged && <AlertTriangle className="w-4 h-4" />}
                    {matchPct}% match
                  </div>
                )}
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500 mb-2 font-medium">ID Face Close-up</p>
                  <img src={app.id_face_crop_url} alt="ID face"
                    className="w-full h-64 object-contain rounded-lg border bg-gray-50" />
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-2 font-medium">Live Face Photo</p>
                  <img src={app.face_photo_url} alt="Live face"
                    className="w-full h-64 object-contain rounded-lg border bg-gray-50" />
                </div>
              </div>
              {app.face_match_flagged && (
                <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  Face match score is below 60% threshold. Please verify identity carefully.
                </div>
              )}
            </div>

            {/* Full ID document */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="font-semibold text-navy mb-3">ID Document</h2>
              <img src={app.id_document_url} alt="ID document"
                className="w-full max-h-96 object-contain rounded-lg border bg-gray-50" />
            </div>
          </div>

          {/* Right: Details & Actions */}
          <div className="space-y-4">
            {/* Person details */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="font-semibold text-navy mb-4">Applicant Details</h2>
              <dl className="space-y-3 text-sm">
                {[
                  ['Name', app.full_name],
                  ['Organization', app.organization],
                  ['Designation', app.designation],
                  ['Email', app.email],
                  ['Phone', app.phone],
                  ['Country', app.country],
                  ['Media Type', app.media_type],
                  ['Submitted', new Date(app.created_at).toLocaleString()],
                ].map(([label, value]) => (
                  <div key={label as string} className="flex justify-between">
                    <dt className="text-gray-500">{label}</dt>
                    <dd className="font-medium text-right capitalize">{value as string}</dd>
                  </div>
                ))}
              </dl>
            </div>

            {/* Status */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="font-semibold text-navy mb-3">Status</h2>
              <div className={`inline-block px-4 py-2 rounded-full font-semibold text-sm ${
                app.status === 'approved' ? 'bg-green-100 text-green-700' :
                app.status === 'rejected' ? 'bg-red-100 text-red-700' :
                'bg-orange-100 text-orange-700'
              }`}>
                {app.status === 'pending_review' ? 'Pending Review' : app.status.toUpperCase()}
              </div>
              {app.admin_notes && <p className="mt-3 text-sm text-gray-600 italic">Notes: {app.admin_notes}</p>}
            </div>

            {/* Actions */}
            {app.status === 'pending_review' && (
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="font-semibold text-navy mb-3">Review Actions</h2>
                <textarea placeholder="Admin notes (optional)" value={notes}
                  onChange={e => setNotes(e.target.value)} rows={3}
                  className="w-full border rounded-lg px-3 py-2 text-sm mb-3 focus:ring-2 focus:ring-saffron" />
                <div className="flex gap-3">
                  <button onClick={() => { setAction('approve'); }}
                    className={`flex-1 py-2 rounded-lg font-medium text-sm flex items-center justify-center gap-1 ${
                      action === 'approve' ? 'bg-green-600 text-white' : 'bg-green-100 text-green-700 hover:bg-green-200'
                    }`}>
                    <CheckCircle className="w-4 h-4" /> Approve
                  </button>
                  <button onClick={() => { setAction('reject'); }}
                    className={`flex-1 py-2 rounded-lg font-medium text-sm flex items-center justify-center gap-1 ${
                      action === 'reject' ? 'bg-red-600 text-white' : 'bg-red-100 text-red-700 hover:bg-red-200'
                    }`}>
                    <XCircle className="w-4 h-4" /> Reject
                  </button>
                </div>
                {action && (
                  <button onClick={handleReview} disabled={submitting}
                    className="w-full mt-3 bg-navy text-white py-2 rounded-lg font-medium text-sm disabled:opacity-50">
                    {submitting ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : `Confirm ${action}`}
                  </button>
                )}
              </div>
            )}

            {/* Credential info */}
            {app.credential && (
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="font-semibold text-navy mb-3">Credential</h2>
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Badge #</dt>
                    <dd className="font-mono font-bold">{app.credential.badge_number}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Expires</dt>
                    <dd>{new Date(app.credential.expires_at).toLocaleDateString()}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Revoked</dt>
                    <dd>{app.credential.is_revoked ? '🔴 Yes' : '🟢 No'}</dd>
                  </div>
                </dl>
                {app.credential.badge_pdf_url && (
                  <a href={app.credential.badge_pdf_url} target="_blank"
                    className="mt-3 flex items-center justify-center gap-2 bg-saffron text-white py-2 rounded-lg text-sm font-medium hover:bg-saffron-dark">
                    <Download className="w-4 h-4" /> Download Badge
                  </a>
                )}
                {!app.credential.is_revoked && (
                  <button onClick={handleRevoke}
                    className="w-full mt-2 border border-red-300 text-red-600 py-2 rounded-lg text-sm hover:bg-red-50">
                    Revoke Credential
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
