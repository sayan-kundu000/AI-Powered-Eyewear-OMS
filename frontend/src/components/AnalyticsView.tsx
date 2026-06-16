import React, { useEffect } from 'react'
import { useOrderStore } from '../store/orderStore'
import { 
  LineChart, 
  Line, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell
} from 'recharts'
import { BarChart3, TrendingUp, ShieldAlert, Award, Star } from 'lucide-react'

export default function AnalyticsView() {
  const { analytics, fetchAnalytics } = useOrderStore()

  useEffect(() => {
    fetchAnalytics()
  }, [])

  if (!analytics) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-3">
        <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-slate-500">Retrieving analytical aggregates...</span>
      </div>
    )
  }

  // Pre-process data
  const dailyData = analytics.daily_orders || []
  const tatData = analytics.tat_trends || []
  const stores = analytics.store_performance || []
  const qcRate = analytics.qc_failure_rate || 0.0

  // Palette
  const colors = ['#6366f1', '#8b5cf6', '#a78bfa', '#c084fc']

  return (
    <div className="space-y-6">
      {/* KPI stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="glass-panel p-5 rounded-2xl border border-slate-900 shadow-md flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">QC Inspection Fail Rate</span>
            <span className="text-2xl font-bold mt-1 block text-rose-400">{qcRate.toFixed(1)}%</span>
            <span className="text-[10px] text-slate-500 block mt-0.5">Sc scratches & axis mismatches</span>
          </div>
          <div className="p-3.5 bg-rose-500/10 text-rose-400 rounded-xl border border-rose-500/20">
            <ShieldAlert className="w-5 h-5 animate-pulse" />
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-900 shadow-md flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Average Progressive TAT</span>
            <span className="text-2xl font-bold mt-1 block text-indigo-400">94.2h</span>
            <span className="text-[10px] text-slate-500 block mt-0.5">From lab blocker to shipping hub</span>
          </div>
          <div className="p-3.5 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
            <TrendingUp className="w-5 h-5" />
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-900 shadow-md flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Top Performing Outlet</span>
            <span className="text-xl font-bold mt-1.5 block truncate max-w-[170px] text-emerald-400">
              {stores.length > 0 ? stores.sort((a,b) => b.performance_score - a.performance_score)[0].store_name : 'N/A'}
            </span>
            <span className="text-[10px] text-slate-500 block mt-0.5">SLA timeliness threshold &gt; 95%</span>
          </div>
          <div className="p-3.5 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20">
            <Award className="w-5 h-5" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily orders trend */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-4">
          <div>
            <h3 className="font-bold text-base text-white">Production Intake Velocity</h3>
            <span className="text-[11px] text-slate-500">Active orders entered during the past 7 days</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dailyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.3} />
                <XAxis dataKey="date" stroke="#64748b" fontSize={10} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#090d16', border: '1px solid #1e293b', borderRadius: '12px' }}
                  labelStyle={{ color: '#94a3b8', fontSize: '10px', fontWeight: 600 }}
                  itemStyle={{ color: '#818cf8', fontSize: '11px' }}
                />
                <Line type="monotone" dataKey="orders" stroke="#6366f1" strokeWidth={3} dot={{ fill: '#6366f1', strokeWidth: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* TAT by Lens type */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-4">
          <div>
            <h3 className="font-bold text-base text-white">Mean Lead Time (TAT)</h3>
            <span className="text-[11px] text-slate-500">Average hours consumed per lens prescription complexity</span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={tatData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.3} />
                <XAxis dataKey="lens_type" stroke="#64748b" fontSize={10} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#090d16', border: '1px solid #1e293b', borderRadius: '12px' }}
                  labelStyle={{ color: '#94a3b8', fontSize: '10px', fontWeight: 600 }}
                  itemStyle={{ color: '#a78bfa', fontSize: '11px' }}
                />
                <Bar dataKey="avg_tat_hours" radius={[8, 8, 0, 0]}>
                  {tatData.map((entry, idx) => (
                    <Cell key={`cell-${idx}`} fill={colors[idx % colors.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Store performance leaderboards */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-4">
        <div>
          <h3 className="font-bold text-base text-white">Retail Outlet Productivity & SLA Score</h3>
          <span className="text-[11px] text-slate-500">Evaluates store demand volumes against production delay instances</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-900 text-slate-500 font-semibold uppercase tracking-wider">
                <th className="pb-3">Rank</th>
                <th className="pb-3">Outlet Name</th>
                <th className="pb-3">City Region</th>
                <th className="pb-3">Total Intake Count</th>
                <th className="pb-3">SLA Compliance Rating</th>
                <th className="pb-3 text-right">Performance Index</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-900/60 text-slate-300">
              {stores.sort((a,b) => b.performance_score - a.performance_score).map((s, idx) => (
                <tr key={s.store_id} className="hover:bg-slate-900/10">
                  <td className="py-3 font-bold text-slate-500">#{idx + 1}</td>
                  <td className="py-3 font-semibold text-slate-200">{s.store_name}</td>
                  <td className="py-3 text-slate-400">{s.location}</td>
                  <td className="py-3 font-mono">{s.order_count}</td>
                  <td className="py-3">
                    <div className="flex items-center space-x-1.5">
                      <div className="w-16 bg-slate-900 h-1.5 rounded-full overflow-hidden border border-slate-800">
                        <div 
                          className={`h-1.5 rounded-full ${s.performance_score >= 85 ? 'bg-emerald-500' : s.performance_score >= 70 ? 'bg-amber-500' : 'bg-rose-500'}`} 
                          style={{ width: `${s.performance_score}%` }} 
                        />
                      </div>
                      <span className="font-bold">{s.performance_score}%</span>
                    </div>
                  </td>
                  <td className="py-3 text-right font-bold text-indigo-400 flex items-center justify-end space-x-1">
                    <Star className="w-3.5 h-3.5 fill-indigo-500/20 text-indigo-400 shrink-0" />
                    <span>{((s.performance_score * 5) / 100).toFixed(2)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
