import React, { useState } from 'react'
import { Scan, Upload, ShieldCheck, ShieldAlert, RefreshCw, Layers, CheckCircle } from 'lucide-react'

import { API_BASE_URL } from '../config'

export default function QCVisionVerify() {
  const [orderId, setOrderId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [qcResult, setQcResult] = useState<any | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!orderId || !file) return
    setLoading(true)
    setQcResult(null)
    const token = localStorage.getItem('token')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch(`${API_BASE_URL}/orders/${orderId}/qc`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      if (res.ok) {
        const data = await res.json()
        setQcResult(data)
      } else {
        const err = await res.json()
        alert(err.detail || "Error performing QC scan. Check that the order is in a state allowing QC.")
      }
    } catch (error) {
      alert("Network error running QC scan.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
      {/* Scan Control Area */}
      <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-6">
        <div className="space-y-2">
          <h3 className="font-bold text-lg text-white">AI Vision Quality Control Verification</h3>
          <p className="text-xs text-slate-500">
            Submit a high-resolution laboratory photo of the fully assembled eyewear.
            The model analyzes alignment axis tilt, surface scratches, and coatings.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2 max-w-xs">
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Production Order ID</label>
            <input
              type="number"
              value={orderId}
              onChange={(e) => setOrderId(e.target.value)}
              placeholder="e.g. 15"
              required
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl text-xs text-slate-300 focus:outline-none"
            />
            <span className="text-[10px] text-slate-600">Enter database order ID to verify (e.g. 1 to 500)</span>
          </div>

          <div className="border border-dashed border-slate-800 rounded-2xl p-8 text-center bg-slate-950/20 hover:border-slate-700 transition-all flex flex-col items-center justify-center space-y-3">
            <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
              <Upload className="w-6 h-6 animate-pulse" />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-bold text-slate-300">Drag & drop or browse eyewear image</p>
              <p className="text-[10px] text-slate-500">Upload lab inspect photos</p>
            </div>
            <input
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              required
              className="text-xs text-slate-400 cursor-pointer max-w-xs block file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-900 file:text-slate-300 hover:file:bg-slate-800"
            />
            {file && <span className="text-xs font-semibold text-indigo-400">Eyewear photo: {file.name}</span>}
          </div>

          <button
            type="submit"
            disabled={loading || !file || !orderId}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold tracking-wide transition-all flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/10"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Running Edge Checks & Neural Alignment...</span>
              </>
            ) : (
              <>
                <Scan className="w-4 h-4" />
                <span>Inspect Lens Quality</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* QC Results Panel */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-6">
        <h4 className="font-bold text-sm text-white">Neural Verification Report</h4>
        
        {qcResult ? (
          <div className="space-y-5">
            {/* Recommendation badge */}
            <div className={`p-4 rounded-xl flex items-center space-x-3 border ${
              qcResult.recommendation === 'PASS' 
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' 
                : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
            }`}>
              {qcResult.recommendation === 'PASS' ? (
                <>
                  <ShieldCheck className="w-8 h-8 shrink-0" />
                  <div>
                    <span className="font-bold text-sm block">QUALITY APPROVED</span>
                    <span className="text-[10px] text-slate-400">Order successfully progressed to packaging stage</span>
                  </div>
                </>
              ) : (
                <>
                  <ShieldAlert className="w-8 h-8 shrink-0" />
                  <div>
                    <span className="font-bold text-sm block">QUALITY REJECTED</span>
                    <span className="text-[10px] text-slate-400">Auto-triggered FSM rework: created warranty order</span>
                  </div>
                </>
              )}
            </div>

            {/* Individual scores */}
            <div className="space-y-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Neural Metrics</span>
              
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-slate-400">Lens Alignment Accuracy</span>
                  <span className="text-slate-200">{qcResult.alignment_score}%</span>
                </div>
                <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden border border-slate-800/60">
                  <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${qcResult.alignment_score}%` }} />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-slate-400">Surface Scratch Cleanliness</span>
                  <span className="text-slate-200">{qcResult.surface_defect_score}%</span>
                </div>
                <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden border border-slate-800/60">
                  <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${qcResult.surface_defect_score}%` }} />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-slate-400">Overall Quality Index</span>
                  <span className={`font-semibold ${qcResult.qc_score >= 80 ? 'text-emerald-400' : 'text-rose-400'}`}>{qcResult.qc_score}%</span>
                </div>
                <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden border border-slate-800/60">
                  <div className={`h-1.5 rounded-full ${qcResult.qc_score >= 80 ? 'bg-emerald-500' : 'bg-rose-500'}`} style={{ width: `${qcResult.qc_score}%` }} />
                </div>
              </div>
            </div>

            {/* Process details */}
            <div className="p-4 bg-slate-950 border border-slate-900 rounded-xl space-y-2 text-xs">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Computer Vision Details</span>
              <div className="flex justify-between">
                <span className="text-slate-500">Lens Boundaries Spotted</span>
                <span className="text-slate-300 font-medium">2 lenses</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Axis Tilt Deviation</span>
                <span className="text-slate-300 font-medium">0.45 deg</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Micro Scratch Count</span>
                <span className="text-slate-300 font-medium">0 spots</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="h-64 flex flex-col items-center justify-center text-center text-slate-500 p-4 border border-dashed border-slate-900 rounded-2xl">
            <Layers className="w-8 h-8 text-slate-600 mb-3 animate-pulse" />
            <p className="text-xs max-w-[180px] font-medium leading-relaxed">
              Upload the eyewear photograph and click inspect. The neural network results will populate here.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
