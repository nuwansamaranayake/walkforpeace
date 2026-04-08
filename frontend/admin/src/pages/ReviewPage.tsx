import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle, XCircle, Loader2, Download, Clock, MapPin } from 'lucide-react'
import {
  getApplication, reviewApplication, revokeCredential, StatusBadge, getApplicationScans,
} from '@walkforpeace/shared'
import type { ApplicationDetail, ScanLogItem } from '@walkforpeace/shared'

export default function ReviewPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [app, setApp] = useState<ApplicationDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [action, setAction] = useState<'approve' | 'reject' | null>(null)
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [scans, setScans] = useState<ScanLogItem[]>([])
  const [scansLoading, setScansLoading] = useState(false)

  const loadApp = async () => {
    if (!id) return
    try {
      const data = await getApplication(id)
      setApp(data)
    } catch {
      navigate('/dashboard')
    } finally {
      setLoading(false)
    }
  }

  const loadScans = async () => {
    if (!id) return
    setScansLoading(true)
    try {
      const data = await getApplicationScans(id)
      setScans(data)
    } catch {
      // scans are optional
    } finally {
      setScansLoading(false)
    }
  }

  useEffect(() => { loadApp(); loadScans() }, [id])

  const handleReview = async () => {
    if (!action || !id) return
    setSubmitting(true)
    try {
      await reviewApplication(id, action, notes)
      const data = await getApplication(id)
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
      const data = await getApplication(id)
      setApp(data)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Revocation failed')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-saffron" />
      </div>
    )
  }
  if (!app) return null

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-navy text-white px-6 py-4">
        <Link to="/dashboard" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-1">
          <ArrowLeft className="w-4 h-4" /> Back to dashboard
        </Link>
        <h1 className="text-lg font-bold text-saffron">Review Application — {app.ref_number}</h1>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left: Photos + Scan History */}
          <div className="lg:col-span-2 space-y-4">
            {/* Identity verification — ID document and live photo side by side */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="font-semibold text-navy mb-4">Identity Verification</h2>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500 mb-2 font-medium">ID Document</p>
                  <img
                    src={app.id_document_url}
                    alt="ID document"
                    className="w-full object-contain rounded-lg border bg-gray-50"
                    style={{ minHeight: '280px', maxHeight: '480px' }}
                  />
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-2 font-medium">Live Face Photo</p>
                  <img
                    src={app.face_photo_url}
                    alt="Live face"
                    className="w-full object-contain rounded-lg border bg-gray-50"
                    style={{ minHeight: '280px', maxHeight: '480px' }}
                  />
                </div>
              </div>
              <p className="mt-3 text-sm text-gray-500">Compare the ID document photo with the live face photo to verify identity.</p>
            </div>

            {/* Scan History */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-navy flex items-center gap-2">
                  <Clock className="w-4 h-4" /> Scan History
                </h2>
                <span className="text-xs bg-navy/10 text-navy px-2 py-1 rounded-full font-medium">
                  {scans.length} scan{scans.length !== 1 ? 's' : ''}
                </span>
              </div>
              {scansLoading ? (
                <p className="text-gray-400 text-sm py-4 text-center">Loading scan history...</p>
              ) : scans.length === 0 ? (
                <p className="text-gray-400 text-sm py-4 text-center">No scans recorded yet</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
                      <tr>
                        <th className="px-3 py-2 text-left">Time</th>
                        <th className="px-3 py-2 text-left">Location</th>
                        <th className="px-3 py-2 text-left">Result</th>
                        <th className="px-3 py-2 text-left">Gate Action</th>
                        <th className="px-3 py-2 text-left">Device</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {scans.map(scan => (
                        <tr key={scan.id} className="text-xs">
                          <td className="px-3 py-2 whitespace-nowrap">{new Date(scan.scanned_at).toLocaleString()}</td>
                          <td className="px-3 py-2">
                            {scan.place_name ? (
                              <span className="flex items-center gap-1">
                                <MapPin className="w-3 h-3 text-gray-400 shrink-0" />
                                {scan.place_name}
                              </span>
                            ) : scan.latitude && scan.longitude ? (
                              <span className="text-gray-400 font-mono">{scan.latitude.toFixed(4)}, {scan.longitude.toFixed(4)}</span>
                            ) : (
                              <span className="text-gray-300">—</span>
                            )}
                          </td>
                          <td className="px-3 py-2">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                              scan.result === 'valid' ? 'bg-green-100 text-green-700' :
                              scan.result === 'expired' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-red-100 text-red-700'
                            }`}>
                              {scan.result}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-gray-500">{scan.verified_by_action ?? '—'}</td>
                          <td className="px-3 py-2 text-gray-400">{scan.device_id ?? scan.scanned_by_ip ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Right: Details & Actions */}
          <div className="space-y-4">
            {/* Person details */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="font-semibold text-navy mb-4">Applicant Details</h2>
              <dl className="space-y-3 text-sm">
                {([
                  ['Name', app.full_name],
                  ['Organization', app.organization],
                  ['Designation', app.designation],
                  ['Email', app.email],
                  ['Phone', app.phone],
                  ['Country', app.country],
                  ['Media Type', app.media_type],
                  ['PIN Code', app.pin_code ?? '—'],
                  ['ID Number', app.id_number ?? '—'],
                  ['Submitted', new Date(app.created_at).toLocaleString()],
                ] as [string, string][]).map(([label, value]) => (
                  <div key={label} className="flex justify-between gap-2">
                    <dt className="text-gray-500 shrink-0">{label}</dt>
                    <dd className="font-medium text-right capitalize break-all">{value}</dd>
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
                app.status === 'revoked' ? 'bg-red-100 text-red-700' :
                'bg-orange-100 text-orange-700'
              }`}>
                {app.status === 'pending_review' ? 'Pending Review' : app.status.toUpperCase()}
              </div>
              {app.admin_notes && (
                <p className="mt-3 text-sm text-gray-600 italic">Notes: {app.admin_notes}</p>
              )}
              {app.reviewed_by && (
                <p className="mt-2 text-xs text-gray-400">
                  Reviewed by {app.reviewed_by}
                  {app.reviewed_at && ` on ${new Date(app.reviewed_at).toLocaleDateString()}`}
                </p>
              )}
            </div>

            {/* Actions */}
            {app.status === 'pending_review' && (
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="font-semibold text-navy mb-3">Review Actions</h2>
                <textarea
                  placeholder="Admin notes (optional)"
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  rows={3}
                  className="w-full border rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-saffron"
                />
                <div className="flex gap-3">
                  <button
                    onClick={() => setAction('approve')}
                    className={`flex-1 py-2 rounded-lg font-medium text-sm flex items-center justify-center gap-1 ${
                      action === 'approve' ? 'bg-green-600 text-white' : 'bg-green-100 text-green-700 hover:bg-green-200'
                    }`}
                  >
                    <CheckCircle className="w-4 h-4" /> Approve
                  </button>
                  <button
                    onClick={() => setAction('reject')}
                    className={`flex-1 py-2 rounded-lg font-medium text-sm flex items-center justify-center gap-1 ${
                      action === 'reject' ? 'bg-red-600 text-white' : 'bg-red-100 text-red-700 hover:bg-red-200'
                    }`}
                  >
                    <XCircle className="w-4 h-4" /> Reject
                  </button>
                </div>
                {action && (
                  <button
                    onClick={handleReview}
                    disabled={submitting}
                    className="w-full mt-3 bg-navy text-white py-2 rounded-lg font-medium text-sm disabled:opacity-50"
                  >
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
                    <dt className="text-gray-500">Verification</dt>
                    <dd><StatusBadge status={app.credential.verification_status} /></dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Issued</dt>
                    <dd>{new Date(app.credential.issued_at).toLocaleDateString()}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Expires</dt>
                    <dd>{new Date(app.credential.expires_at).toLocaleDateString()}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Revoked</dt>
                    <dd className={app.credential.is_revoked ? 'text-red-600 font-medium' : 'text-green-600'}>
                      {app.credential.is_revoked ? 'Yes' : 'No'}
                    </dd>
                  </div>
                </dl>
                {app.credential.badge_pdf_url && (
                  <a
                    href={app.credential.badge_pdf_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 flex items-center justify-center gap-2 bg-saffron text-white py-2 rounded-lg text-sm font-medium hover:bg-saffron-dark"
                  >
                    <Download className="w-4 h-4" /> Download Badge
                  </a>
                )}
                {!app.credential.is_revoked && (
                  <button
                    onClick={handleRevoke}
                    className="w-full mt-2 border border-red-300 text-red-600 py-2 rounded-lg text-sm hover:bg-red-50"
                  >
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
