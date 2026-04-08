import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LogOut, LayoutDashboard, ChevronLeft, ChevronRight, Search } from 'lucide-react'
import { getVerificationLogs } from '@walkforpeace/shared'
import type { VerificationLogItem } from '@walkforpeace/shared'

function ResultBadge({ result }: { result: string }) {
  if (result === 'valid') {
    return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">valid</span>
  }
  if (result === 'expired') {
    return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">expired</span>
  }
  if (result === 'invalid' || result === 'revoked') {
    return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">{result}</span>
  }
  return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">{result}</span>
}

function GateActionBadge({ action }: { action: string | null }) {
  if (!action) return <span className="text-gray-300 text-xs">—</span>
  if (action === 'gate_approved') {
    return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">gate_approved</span>
  }
  if (action === 'gate_denied') {
    return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">gate_denied</span>
  }
  return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">{action}</span>
}

export default function LogsPage() {
  const [logs, setLogs] = useState<VerificationLogItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const navigate = useNavigate()
  const pageSize = 20

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const data = await getVerificationLogs({
        page,
        page_size: pageSize,
        ...(search && { search }),
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
      })
      setLogs(data.items)
      setTotal(data.total)
    } catch (err: any) {
      if (err.response?.status === 401) navigate('/')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchLogs() }, [page, search, dateFrom, dateTo])

  const totalPages = Math.ceil(total / pageSize)

  const handleLogout = () => {
    localStorage.removeItem('admin_token')
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar */}
      <div className="bg-navy text-white px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-saffron">Verification Logs</h1>
          <p className="text-xs text-gray-400">Walk for Peace Media Credentials</p>
        </div>
        <div className="flex items-center gap-4">
          <Link to="/dashboard" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm">
            <LayoutDashboard className="w-4 h-4" /> Dashboard
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
        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm p-4 mb-6 flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-gray-400" />
            <input
              placeholder="Search badge number, name..."
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }}
              className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-saffron"
            />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <label className="text-gray-500 shrink-0">From:</label>
            <input
              type="date"
              value={dateFrom}
              onChange={e => { setDateFrom(e.target.value); setPage(1) }}
              className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-saffron"
            />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <label className="text-gray-500 shrink-0">To:</label>
            <input
              type="date"
              value={dateTo}
              onChange={e => { setDateTo(e.target.value); setPage(1) }}
              className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-saffron"
            />
          </div>
          {(search || dateFrom || dateTo) && (
            <button
              onClick={() => { setSearch(''); setDateFrom(''); setDateTo(''); setPage(1) }}
              className="text-sm text-gray-400 hover:text-gray-600 border rounded-lg px-3 py-2"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Timestamp</th>
                  <th className="px-4 py-3 text-left">Badge #</th>
                  <th className="px-4 py-3 text-left">Name</th>
                  <th className="px-4 py-3 text-left">Result</th>
                  <th className="px-4 py-3 text-left">Gate Action</th>
                  <th className="px-4 py-3 text-left">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {loading ? (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>
                ) : logs.length === 0 ? (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No verification logs found</td></tr>
                ) : logs.map(log => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                      {new Date(log.scanned_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs font-medium">{log.badge_number}</td>
                    <td className="px-4 py-3 text-gray-700">{log.full_name}</td>
                    <td className="px-4 py-3"><ResultBadge result={log.result} /></td>
                    <td className="px-4 py-3"><GateActionBadge action={log.verified_by_action} /></td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-400">{log.scanned_by_ip}</td>
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
