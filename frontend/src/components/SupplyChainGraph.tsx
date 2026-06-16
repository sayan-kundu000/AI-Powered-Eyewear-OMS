import React, { useEffect, useState } from 'react'
import { Network, Activity, Truck, AlertOctagon, HelpCircle, ArrowRight, Activity as FlowIcon } from 'lucide-react'

import { API_BASE_URL } from '../config'

export default function SupplyChainGraph() {
  const [data, setData] = useState<any | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadGraphData()
  }, [])

  const loadGraphData = async () => {
    setLoading(true)
    const token = localStorage.getItem('token')
    try {
      const res = await fetch(`${API_BASE_URL}/analytics/supply-chain`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const result = await res.json()
        setData(result)
      }
    } catch (error) {
      console.error("Failed to load supply chain analysis:", error)
    } finally {
      setLoading(false)
    }
  }

  if (loading || !data) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-3">
        <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-slate-500">Mapping supply chain topology...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Network bottleneck metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="glass-panel p-5 rounded-2xl border border-slate-900 shadow-md flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Max Sourcing Latency</span>
            <span className="text-2xl font-bold mt-1 block text-indigo-400">{data.system_max_lead_time_hours} Hours</span>
            <span className="text-[10px] text-slate-500 block mt-0.5">From vendor dispatch to store shelf</span>
          </div>
          <div className="p-3.5 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
            <Truck className="w-5 h-5" />
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-900 shadow-md flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Primary Central Bottleneck</span>
            <span className="text-xl font-bold mt-1.5 block text-amber-400 truncate max-w-[170px]">
              {data.bottlenecks?.[0]?.node || 'Main Lab'}
            </span>
            <span className="text-[10px] text-slate-500 block mt-0.5">Highest centrality flow quotient</span>
          </div>
          <div className="p-3.5 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20">
            <Activity className="w-5 h-5" />
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-900 shadow-md flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">High Risk Vendors</span>
            <span className="text-2xl font-bold mt-1 block text-rose-400">
              {data.critical_vendors?.length || 0} Vendors
            </span>
            <span className="text-[10px] text-slate-500 block mt-0.5">Reliability rating below 90%</span>
          </div>
          <div className="p-3.5 bg-rose-500/10 text-rose-400 rounded-xl border border-rose-500/20">
            <AlertOctagon className="w-5 h-5 animate-pulse" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Visual pipeline graph */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-6">
          <div>
            <h3 className="font-bold text-base text-white">Visual Supply Chain Nodes Map</h3>
            <p className="text-xs text-slate-500">Directed procurement flow graph from sourcing to store delivery</p>
          </div>

          <div className="relative p-6 bg-slate-950/40 border border-slate-900 rounded-2xl space-y-8 overflow-hidden min-h-[300px]">
            {/* Grid background styling */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#111726_1px,transparent_1px),linear-gradient(to_bottom,#111726_1px,transparent_1px)] bg-[size:24px_24px] opacity-40 pointer-events-none" />

            <div className="relative z-10 grid grid-cols-4 gap-4 items-center justify-items-center h-full text-center">
              {/* Column 1: Sourcing */}
              <div className="space-y-6">
                <span className="text-[9px] font-bold text-indigo-400 uppercase tracking-widest block mb-2">1. Sourcing</span>
                
                <div className="w-28 p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1.5 shadow-md">
                  <span className="text-[10px] font-bold block text-slate-200">Vendor A</span>
                  <span className="text-[8px] bg-emerald-500/10 text-emerald-400 px-1 py-0.2 rounded font-semibold uppercase">Premium (98%)</span>
                </div>
                
                <div className="w-28 p-3 bg-slate-900 border border-rose-500/30 rounded-xl space-y-1.5 shadow-md">
                  <span className="text-[10px] font-bold block text-slate-200">Vendor B</span>
                  <span className="text-[8px] bg-rose-500/10 text-rose-400 px-1 py-0.2 rounded font-semibold uppercase">Economy (85%)</span>
                </div>
              </div>

              {/* Column 2: Labs */}
              <div className="space-y-6">
                <span className="text-[9px] font-bold text-indigo-400 uppercase tracking-widest block mb-2">2. Processing</span>
                
                <div className="w-28 p-3.5 bg-indigo-950/20 border-2 border-indigo-500/40 rounded-xl space-y-1.5 shadow-lg shadow-indigo-950/40 relative">
                  <span className="absolute -top-1.5 -right-1.5 w-3 h-3 rounded-full bg-amber-400 ring-2 ring-[#070b13] animate-pulse" />
                  <span className="text-[10px] font-bold block text-white">Main Lab</span>
                  <span className="text-[8px] text-indigo-400 block font-semibold">Central Hub</span>
                </div>
              </div>

              {/* Column 3: Logistics */}
              <div className="space-y-6">
                <span className="text-[9px] font-bold text-indigo-400 uppercase tracking-widest block mb-2">3. Transit</span>
                
                <div className="w-28 p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1 shadow-md">
                  <span className="text-[10px] font-bold block text-slate-200">Hub North</span>
                  <span className="text-[8px] text-slate-500 block">Bangalore</span>
                </div>

                <div className="w-28 p-3 bg-slate-900 border border-slate-800 rounded-xl space-y-1 shadow-md">
                  <span className="text-[10px] font-bold block text-slate-200">Hub South</span>
                  <span className="text-[8px] text-slate-500 block">Chennai</span>
                </div>
              </div>

              {/* Column 4: Stores */}
              <div className="space-y-6">
                <span className="text-[9px] font-bold text-indigo-400 uppercase tracking-widest block mb-2">4. Outlets</span>
                
                <div className="w-24 p-2 bg-slate-900/60 border border-slate-800 rounded-lg text-[9px] font-bold text-slate-400">
                  Stores 1 - 5
                </div>

                <div className="w-24 p-2 bg-slate-900/60 border border-slate-800 rounded-lg text-[9px] font-bold text-slate-400">
                  Stores 6 - 10
                </div>
              </div>
            </div>

            {/* Glowing lines connectors mockup using SVG */}
            <div className="absolute inset-0 pointer-events-none z-0">
              <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="glowGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#ef4444" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity="0.4" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
          </div>
        </div>

        {/* Bottlenecks side panel */}
        <div className="space-y-6">
          {/* Critical path info */}
          <div className="glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-4">
            <h4 className="font-bold text-sm text-white">Systemic Slowest Path</h4>
            <div className="p-3.5 bg-slate-950 border border-slate-900 rounded-xl space-y-3 text-xs">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Bottleneck Procurement Node Chain</span>
              
              <div className="flex flex-col space-y-2.5">
                {data.slowest_supply_path?.map((node: string, index: number) => (
                  <div key={node} className="flex items-center space-x-2">
                    <div className="w-5 h-5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-[10px] text-indigo-400 font-bold">
                      {index + 1}
                    </div>
                    <span className="font-semibold text-slate-300">{node}</span>
                    {index < data.slowest_supply_path.length - 1 && (
                      <ArrowRight className="w-3 h-3 text-slate-600 shrink-0" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Critical vendors warnings */}
          <div className="glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-4">
            <h4 className="font-bold text-sm text-white">Risk Audits</h4>
            <div className="space-y-3">
              {data.critical_vendors?.map((cv: any) => (
                <div key={cv.vendor} className="p-3.5 bg-rose-500/5 border border-rose-500/10 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center space-x-2 text-rose-400">
                    <AlertOctagon className="w-4 h-4 shrink-0" />
                    <span className="font-bold">{cv.vendor}</span>
                  </div>
                  <p className="text-[10px] text-slate-400 font-medium leading-relaxed">
                    Sourcing from this node risks SLA delay because of lower reliability index rating ({cv.reliability * 100}%).
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
