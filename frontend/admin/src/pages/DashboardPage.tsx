import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Users, Clock, CheckCircle, XCircle, AlertTriangle,
  Search, LogOut, ChevronLeft, ChevronRight, ClipboardList,
  ScanLine, ShieldCheck, Smartphone, MapPin,
} from 'lucide-react'
import {
  getApplications, getStats, batchApprove, getGatekeepers, StatusBadge,
} from '@walkforpeace/shared'
import type { DashboardStats, ApplicationListItem, GatekeeperInfo } from '@walkforpeace/shared'

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [apps, setApps] = useState<ApplicationListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({ status: '', media_type: '', search: '', flagged: '' })
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [batchLoading, setBatchLoading] = useState(false)
  const [gatekeepers, setGatekeepers] = useState<GatekeeperInfo[]>([])
  const navigate = useNavigate()
  const pageSize = 15

  const fetchData = async () => {
    setLoading(true)
    try {
      const [statsData, appsData, gkData] = await Promise.all([
        getStats(),
        getApplications({
          page,
          page_size: pageSize,
          ...(filters.status && { status: filters.status }),
          ...(filters.media_type && { media_type: filters.media_type }),
          ...(filters.search && { search: filters.search }),
          ...(filters.flagged && { flagged: filters.flagged === 'true' }),
        }),
        getGatekeepers().catch(() => []),
      ])
      setStats(statsData)
      setApps(appsData.items)
      setTotal(appsData.total)
      setSelected(new Set())
      setGatekeepers(gkData)
    } catch (err: any) {
      if (err.response?.status === 401) navigate('/')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [page, filters])

  // Auto-refresh gatekeepers every 30s
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const [s, gk] = await Promise.all([getStats(), getGatekeepers().catch(() => [])])
        setStats(s)
        setGatekeepers(gk)
      } catch { /* ignore */ }
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  const totalPages = Math.ceil(total / pageSize)

  const statCards = stats ? [
    { label: 'Total', value: stats.total_registered, icon: Users, color: 'bg-blue-500' },
    { label: 'Pending', value: stats.pending, icon: Clock, color: 'bg-saffron' },
    { label: 'Approved', value: stats.approved, icon: CheckCircle, color: 'bg-green-500' },
    { label: 'Rejected', value: stats.rejected, icon: XCircle, color: 'bg-red-500' },
    { label: 'Scans Today', value: stats.total_scans_today, icon: ScanLine, color: 'bg-purple-500' },
    { label: 'Gatekeepers', value: stats.active_gatekeepers, icon: ShieldCheck, color: 'bg-teal-500' },
  ] : []

  const toggleSelect = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selected.size === apps.length && apps.length > 0) {
      setSelected(new Set())
    } else {
      setSelected(new Set(apps.map(a => a.id)))
    }
  }

  const handleBatchApprove = async () => {
    if (selected.size === 0) return
    if (!confirm(`Approve ${selected.size} selected application(s)?`)) return
    setBatchLoading(true)
    try {
      const result = await batchApprove(Array.from(selected))
      alert(result.message || `${result.approved_count} applications approved.`)
      fetchData()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Batch approve failed')
    } finally {
      setBatchLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('admin_token')
    navigate('/')
  }

  function timeAgo(dateStr: string | null): string {
    if (!dateStr) return 'Never'
    const diff = Date.now() - new Date(dateStr).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'Just now'
    if (mins < 60) return `${mins} min ago`
    const hrs = Math.floor(mins / 60)
    return `${hrs}h ago`
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar */}
      <div className="bg-navy text-white px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src="/logo.png" alt="" className="w-8 h-8 object-contain" />
          <div>
            <h1 className="text-lg font-bold text-saffron">Admin Dashboard</h1>
            <p className="text-xs text-gray-400">Walk for Peace Media Credentials</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <Link to="/logs" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm">
            <ClipboardList className="w-4 h-4" /> Logs
          </Link>
          <button
            onClick={handleLogout}
            className="text-gray-400 hover:text-white flex items-center gap-1 text-sm"
          >
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-6">
          {statCards.map(s => (
            <div key={s.label} className={`${s.color} text-white rounded-xl p-4 text-center`}>
              <s.icon className="w-6 h-6 mx-auto mb-1 opacity-80" />
              <div className="text-2xl font-bold">{s.value}</div>
              <div className="text-xs opacity-80">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Gatekeeper Monitor */}
        {gatekeepers.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-4 mb-6">
            <h2 className="font-semibold text-navy mb-3 flex items-center gap-2 text-sm">
              <ShieldCheck className="w-4 h-4" /> Active Gatekeepers
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-gray-50 text-gray-500 uppercase">
                  <tr>
                    <th className="px-3 py-2 text-left">Device</th>
                    <th className="px-3 py-2 text-left">IP</th>
                    <th className="px-3 py-2 text-left">Location</th>
                    <th className="px-3 py-2 text-left">Scans</th>
                    <th className="px-3 py-2 text-left">Last Active</th>
                    <th className="px-3 py-2 text-left">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {gatekeepers.map(gk => (
                    <tr key={gk.id}>
                      <td className="px-3 py-2">
                        <span className="flex items-center gap-1.5">
                          <Smartphone className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                          <span className="font-medium">{gk.device_name || 'Unknown'}</span>
                        </span>
                        {gk.screen_size && <span className="text-gray-400 ml-5">{gk.screen_size}</span>}
                      </td>
                      <td className="px-3 py-2 text-gray-500 font-mono">{gk.device_ip || '—'}</td>
                      <td className="px-3 py-2">
                        {gk.last_location ? (
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3 h-3 text-gray-400 shrink-0" />
                            {gk.last_location}
                          </span>
                        ) : '—'}
                      </td>
                      <td className="px-3 py-2 font-bold">{gk.total_scans}</td>
                      <td className="px-3 py-2 text-gray-500">{timeAgo(gk.last_scan_at)}</td>
                      <td className="px-3 py-2">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                          gk.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${gk.status === 'active' ? 'bg-green-500' : 'bg-red-500'}`} />
                          {gk.status === 'active' ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Filters + Batch Approve */}
        <div className="bg-white rounded-xl shadow-sm p-4 mb-6 flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-gray-400" />
            <input
              placeholder="Search name, org, ref..."
              value={filters.search}
              onChange={e => { setFilters(f => ({ ...f, search: e.target.value })); setPage(1) }}
              className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-saffron"
            />
          </div>
          <select
            value={filters.status}
            onChange={e => { setFilters(f => ({ ...f, status: e.target.value })); setPage(1) }}
            className="border rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            <option value="pending_review">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="revoked">Revoked</option>
          </select>
          <select
            value={filters.media_type}
            onChange={e => { setFilters(f => ({ ...f, media_type: e.target.value })); setPage(1) }}
            className="border rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All types</option>
            <option value="print">Print</option>
            <option value="tv">TV</option>
            <option value="radio">Radio</option>
            <option value="online">Online</option>
            <option value="photographer">Photographer</option>
            <option value="freelance">Freelance</option>
          </select>
          {selected.size > 0 && (
            <button
              onClick={handleBatchApprove}
              disabled={batchLoading}
              className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
            >
              <CheckCircle className="w-4 h-4" />
              {batchLoading ? 'Approving...' : `Batch Approve (${selected.size})`}
            </button>
          )}
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
                <tr>
                  <th className="px-4 py-3 text-left w-10">
                    <input
                      type="checkbox"
                      checked={apps.length > 0 && selected.size === apps.length}
                      onChange={toggleSelectAll}
                      className="rounded"
                    />
                  </th>
                  <th className="px-4 py-3 text-left">Ref #</th>
                  <th className="px-4 py-3 text-left">Name</th>
                  <th className="px-4 py-3 text-left">Organization</th>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">PIN</th>
                  <th className="px-4 py-3 text-left">ID Number</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Date</th>
                  <th className="px-4 py-3 text-left">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {loading ? (
                  <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
                ) : apps.length === 0 ? (
                  <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-400">No applications found</td></tr>
                ) : apps.map(app => (
                  <tr key={app.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selected.has(app.id)}
                        onChange={() => toggleSelect(app.id)}
                        className="rounded"
                      />
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">{app.ref_number}</td>
                    <td className="px-4 py-3 font-medium">{app.full_name}</td>
                    <td className="px-4 py-3 text-gray-600">{app.organization}</td>
                    <td className="px-4 py-3">
                      <span className="bg-navy/10 text-navy px-2 py-0.5 rounded text-xs capitalize">{app.media_type}</span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">
                      {app.pin_code ?? <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">
                      {app.id_number ?? <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={app.status === 'pending_review' ? 'pending' : app.status as any} />
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{new Date(app.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3">
                      <Link to={`/review/${app.id}`} className="text-saffron hover:underline text-xs font-medium">
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
              <span className="text-gray-500">
                Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1 border rounded disabled:opacity-30"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1 border rounded disabled:opacity-30"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
