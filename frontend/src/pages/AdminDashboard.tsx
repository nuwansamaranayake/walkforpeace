import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Users, Clock, CheckCircle, XCircle, AlertTriangle, Search, LogOut, ChevronLeft, ChevronRight } from 'lucide-react'
import { getApplications, getStats } from '../services/api'

export default function AdminDashboard() {
  const [stats, setStats] = useState<any>(null)
  const [apps, setApps] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({ status: '', media_type: '', search: '', flagged: '' })
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const pageSize = 15

  const fetchData = async () => {
    setLoading(true)
    try {
      const [statsRes, appsRes] = await Promise.all([
        getStats(),
        getApplications({
          page, page_size: pageSize,
          ...(filters.status && { status: filters.status }),
          ...(filters.media_type && { media_type: filters.media_type }),
          ...(filters.search && { search: filters.search }),
          ...(filters.flagged && { flagged: filters.flagged === 'true' }),
        }),
      ])
      setStats(statsRes.data)
      setApps(appsRes.data.items)
      setTotal(appsRes.data.total)
    } catch (err: any) {
      if (err.response?.status === 401) navigate('/admin')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [page, filters])

  const totalPages = Math.ceil(total / pageSize)

  const statCards = stats ? [
    { label: 'Total', value: stats.total_registered, icon: Users, color: 'bg-blue-500' },
    { label: 'Pending', value: stats.pending, icon: Clock, color: 'bg-saffron' },
    { label: 'Approved', value: stats.approved, icon: CheckCircle, color: 'bg-green-500' },
    { label: 'Rejected', value: stats.rejected, icon: XCircle, color: 'bg-red-500' },
    { label: 'Flagged', value: stats.flagged_face_match, icon: AlertTriangle, color: 'bg-yellow-500' },
  ] : []

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      pending_review: 'bg-orange-100 text-orange-700',
      approved: 'bg-green-100 text-green-700',
      rejected: 'bg-red-100 text-red-700',
    }
    return map[status] || 'bg-gray-100 text-gray-700'
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar */}
      <div className="bg-navy text-white px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-saffron">Admin Dashboard</h1>
          <p className="text-xs text-gray-400">Walk for Peace Media Credentials</p>
        </div>
        <button onClick={() => { localStorage.removeItem('admin_token'); navigate('/admin') }}
          className="text-gray-400 hover:text-white flex items-center gap-1 text-sm">
          <LogOut className="w-4 h-4" /> Logout
        </button>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          {statCards.map(s => (
            <div key={s.label} className={`${s.color} text-white rounded-xl p-4 text-center`}>
              <s.icon className="w-6 h-6 mx-auto mb-1 opacity-80" />
              <div className="text-2xl font-bold">{s.value}</div>
              <div className="text-xs opacity-80">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm p-4 mb-6 flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-gray-400" />
            <input placeholder="Search name, org, ref..." value={filters.search}
              onChange={e => { setFilters(f => ({ ...f, search: e.target.value })); setPage(1) }}
              className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-saffron" />
          </div>
          <select value={filters.status} onChange={e => { setFilters(f => ({ ...f, status: e.target.value })); setPage(1) }}
            className="border rounded-lg px-3 py-2 text-sm">
            <option value="">All statuses</option>
            <option value="pending_review">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
          <select value={filters.media_type} onChange={e => { setFilters(f => ({ ...f, media_type: e.target.value })); setPage(1) }}
            className="border rounded-lg px-3 py-2 text-sm">
            <option value="">All types</option>
            <option value="print">Print</option>
            <option value="tv">TV</option>
            <option value="radio">Radio</option>
            <option value="online">Online</option>
            <option value="photographer">Photographer</option>
            <option value="freelance">Freelance</option>
          </select>
          <select value={filters.flagged} onChange={e => { setFilters(f => ({ ...f, flagged: e.target.value })); setPage(1) }}
            className="border rounded-lg px-3 py-2 text-sm">
            <option value="">All matches</option>
            <option value="true">Flagged only</option>
          </select>
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Ref #</th>
                  <th className="px-4 py-3 text-left">Name</th>
                  <th className="px-4 py-3 text-left">Organization</th>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Face Match</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Date</th>
                  <th className="px-4 py-3 text-left">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {loading ? (
                  <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
                ) : apps.length === 0 ? (
                  <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No applications found</td></tr>
                ) : apps.map(app => (
                  <tr key={app.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs">{app.ref_number}</td>
                    <td className="px-4 py-3 font-medium">{app.full_name}</td>
                    <td className="px-4 py-3 text-gray-600">{app.organization}</td>
                    <td className="px-4 py-3">
                      <span className="bg-navy/10 text-navy px-2 py-0.5 rounded text-xs capitalize">{app.media_type}</span>
                    </td>
                    <td className="px-4 py-3">
                      {app.face_match_score !== null ? (
                        <span className={`font-mono text-xs ${app.face_match_flagged ? 'text-red-500 font-bold' : 'text-green-600'}`}>
                          {(app.face_match_score * 100).toFixed(0)}%
                          {app.face_match_flagged && <AlertTriangle className="inline w-3 h-3 ml-1" />}
                        </span>
                      ) : <span className="text-gray-400 text-xs">N/A</span>}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge(app.status)}`}>
                        {app.status === 'pending_review' ? 'Pending' : app.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{new Date(app.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3">
                      <Link to={`/admin/review/${app.id}`} className="text-saffron hover:underline text-xs font-medium">
                        Review →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t text-sm">
              <span className="text-gray-500">Showing {(page-1)*pageSize+1}–{Math.min(page*pageSize, total)} of {total}</span>
              <div className="flex gap-2">
                <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1 border rounded disabled:opacity-30"><ChevronLeft className="w-4 h-4" /></button>
                <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1 border rounded disabled:opacity-30"><ChevronRight className="w-4 h-4" /></button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
