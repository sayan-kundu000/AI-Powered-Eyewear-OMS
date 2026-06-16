import React, { useState } from 'react'
import { FileText, Upload, RefreshCw, Check, AlertTriangle, Eye, Search } from 'lucide-react'

import { API_BASE_URL } from '../config'

export default function PrescriptionUpload() {
  const [activeTab, setActiveTab] = useState<'scan' | 'manual'>('scan')
  
  // Input fields
  const [customerId, setCustomerId] = useState(1)
  const [file, setFile] = useState<File | null>(null)
  
  // Optical details
  const [sphOd, setSphOd] = useState(-2.00)
  const [cylOd, setCylOd] = useState(-0.50)
  const [axisOd, setAxisOd] = useState(180)
  const [addOd, setAddOd] = useState(1.50)
  
  const [sphOs, setSphOs] = useState(-2.25)
  const [cylOs, setCylOs] = useState(-0.75)
  const [axisOs, setAxisOs] = useState(175)
  const [addOs, setAddOs] = useState(1.50)
  
  const [pd, setPd] = useState(63.0)

  // Statuses
  const [loading, setLoading] = useState(false)
  const [ocrResult, setOcrResult] = useState<any | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [similarRx, setSimilarRx] = useState<any[]>([])
  const [searchingSimilar, setSearchingSimilar] = useState(false)

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    const token = localStorage.getItem('token')
    try {
      const res = await fetch(`${API_BASE_URL}/prescriptions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          customer_id: Number(customerId),
          sph_od: Number(sphOd),
          cyl_od: Number(cylOd),
          axis_od: Number(axisOd),
          add_od: Number(addOd),
          sph_os: Number(sphOs),
          cyl_os: Number(cylOs),
          axis_os: Number(axisOs),
          add_os: Number(addOs),
          pd: Number(pd)
        })
      })

      if (res.ok) {
        const data = await res.json()
        alert(`Prescription #${data.id} created and validated!`)
        // Reset form or load similarity search
        handleFindSimilar(data)
      } else {
        const err = await res.json()
        alert(err.detail || "Error creating prescription")
      }
    } catch (error) {
      alert("Network error creating prescription")
    } finally {
      setLoading(false)
    }
  }

  const handleOcrSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return
    setLoading(true)
    setOcrResult(null)
    const token = localStorage.getItem('token')
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const res = await fetch(`${API_BASE_URL}/ocr?customer_id=${customerId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      if (res.ok) {
        const data = await res.json()
        setOcrResult(data)
        // Set values from OCR
        const ext = data.extracted_values
        setSphOd(ext.sph_od)
        setCylOd(ext.cyl_od)
        setAxisOd(ext.axis_od)
        setAddOd(ext.add_od)
        setSphOs(ext.sph_os)
        setCylOs(ext.cyl_os)
        setAxisOs(ext.axis_os)
        setAddOs(ext.add_os)
        setPd(ext.pd)
      } else {
        const err = await res.json()
        alert(err.detail || "Error extracting prescription OCR")
      }
    } catch (error) {
      alert("Network error processing OCR")
    } finally {
      setLoading(false)
    }
  }

  const handleManualApprove = async () => {
    if (!ocrResult) return
    setLoading(true)
    const token = localStorage.getItem('token')
    try {
      // Manual approval updates values from state just in case user edited them
      // and approves the prescription
      const res = await fetch(`${API_BASE_URL}/prescriptions/${ocrResult.prescription_id}/validate`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (res.ok) {
        const data = await res.json()
        alert(`OCR Prescription verified and approved successfully!`)
        handleFindSimilar(data)
        setOcrResult(null)
        setFile(null)
      } else {
        const err = await res.json()
        alert(err.detail || "Approval failed")
      }
    } catch (err) {
      alert("Error approving prescription")
    } finally {
      setLoading(false)
    }
  }

  const handleFindSimilar = async (rxData: any) => {
    setSearchingSimilar(true)
    const token = localStorage.getItem('token')
    try {
      // First generate vector embeddings from parameters
      const embRes = await fetch(`${API_BASE_URL}/prescriptions/embeddings/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          sph: rxData.sph_od,
          cyl: rxData.cyl_od,
          axis: rxData.axis_od,
          add_val: rxData.add_od
        })
      })
      
      if (embRes.ok) {
        const { embedding } = await embRes.json()
        
        // Search similar in DB
        const searchRes = await fetch(`${API_BASE_URL}/prescriptions/embeddings/search`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            embedding,
            top_k: 3,
            metric: "cosine"
          })
        })
        if (searchRes.ok) {
          const list = await searchRes.json()
          setSimilarRx(list)
        }
      }
    } catch (error) {
      console.error("Similarity search failed:", error)
    } finally {
      setSearchingSimilar(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Tab select */}
      <div className="flex border-b border-slate-900">
        <button
          onClick={() => { setActiveTab('scan'); setOcrResult(null); }}
          className={`px-5 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'scan' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          AI OCR Scan Upload
        </button>
        <button
          onClick={() => { setActiveTab('manual'); setOcrResult(null); }}
          className={`px-5 py-3 text-sm font-semibold border-b-2 transition-all ${
            activeTab === 'manual' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Manual Prescription Entry
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Main Work Area */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-6">
          <div className="space-y-2">
            <h3 className="font-bold text-lg text-white">
              {activeTab === 'scan' ? 'Automated Prescription OCR Digitization' : 'Optical Parameter Entry'}
            </h3>
            <p className="text-xs text-slate-500">
              {activeTab === 'scan' 
                ? 'Upload prescription image/PDF. Our vision models parse metrics and flag validation requirements.' 
                : 'Directly type in sphere, cylinder, axis, and pupillary distance values for production order.'}
            </p>
          </div>

          <div className="space-y-5">
            {/* Customer select */}
            <div className="space-y-2 max-w-xs">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Customer Association</label>
              <input
                type="number"
                value={customerId}
                onChange={(e) => setCustomerId(Number(e.target.value))}
                min={1}
                max={100}
                required
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl text-xs text-slate-300 focus:outline-none"
              />
              <span className="text-[10px] text-slate-600">Select simulated Customer ID (1 - 100)</span>
            </div>

            {activeTab === 'scan' ? (
              /* OCR UPLOAD FORM */
              <form onSubmit={handleOcrSubmit} className="space-y-6">
                <div className="border border-dashed border-slate-800 rounded-2xl p-8 text-center bg-slate-950/20 hover:border-slate-700 transition-all flex flex-col items-center justify-center space-y-3">
                  <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
                    <Upload className="w-6 h-6 animate-pulse" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs font-bold text-slate-300">Drag & drop or browse for files</p>
                    <p className="text-[10px] text-slate-500">Supports JPG, PNG, PDF prescriptions up to 500MB</p>
                  </div>
                  <input
                    type="file"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    required
                    className="text-xs text-slate-400 cursor-pointer max-w-xs block file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-slate-900 file:text-slate-300 hover:file:bg-slate-800"
                  />
                  {file && <span className="text-xs font-semibold text-indigo-400">Selected: {file.name}</span>}
                </div>

                <button
                  type="submit"
                  disabled={loading || !file}
                  className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold tracking-wide transition-all flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/10"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Extracting OCR Texts...</span>
                    </>
                  ) : (
                    <>
                      <FileText className="w-4 h-4" />
                      <span>Process AI OCR Scan</span>
                    </>
                  )}
                </button>
              </form>
            ) : (
              /* MANUAL ENTRY FORM */
              <form onSubmit={handleManualSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* OD */}
                  <div className="p-4 bg-slate-950 border border-slate-900 rounded-2xl space-y-4">
                    <h4 className="font-bold text-xs text-indigo-400 border-b border-slate-900 pb-2">Right Eye (Oculus Dexter - OD)</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-semibold text-slate-500 uppercase">Sphere (SPH)</label>
                        <input type="number" step="0.25" value={sphOd} onChange={e => setSphOd(Number(e.target.value))} className="w-full px-3 py-2 bg-slate-900 border border-slate-800 text-xs rounded-xl text-slate-300 focus:outline-none" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-semibold text-slate-500 uppercase">Cylinder (CYL)</label>
                        <input type="number" step="0.25" value={cylOd} onChange={e => setCylOd(Number(e.target.value))} className="w-full px-3 py-2 bg-slate-900 border border-slate-800 text-xs rounded-xl text-slate-300 focus:outline-none" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-semibold text-slate-500 uppercase">Axis</label>
                        <input type="number" value={axisOd} onChange={e => setAxisOd(Number(e.target.value))} className="w-full px-3 py-2 bg-slate-900 border border-slate-800 text-xs rounded-xl text-slate-300 focus:outline-none" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-semibold text-slate-500 uppercase">Add</label>
                        <input type="number" step="0.25" value={addOd} onChange={e => setAddOd(Number(e.target.value))} className="w-full px-3 py-2 bg-slate-900 border border-slate-800 text-xs rounded-xl text-slate-300 focus:outline-none" />
                      </div>
                    </div>
                  </div>

                  {/* OS */}
                  <div className="p-4 bg-slate-950 border border-slate-900 rounded-2xl space-y-4">
                    <h4 className="font-bold text-xs text-indigo-400 border-b border-slate-900 pb-2">Left Eye (Oculus Sinister - OS)</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-semibold text-slate-500 uppercase">Sphere (SPH)</label>
                        <input type="number" step="0.25" value={sphOs} onChange={e => setSphOs(Number(e.target.value))} className="w-full px-3 py-2 bg-slate-900 border border-slate-800 text-xs rounded-xl text-slate-300 focus:outline-none" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-semibold text-slate-500 uppercase">Cylinder (CYL)</label>
                        <input type="number" step="0.25" value={cylOs} onChange={e => setCylOs(Number(e.target.value))} className="w-full px-3 py-2 bg-slate-900 border border-slate-800 text-xs rounded-xl text-slate-300 focus:outline-none" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-semibold text-slate-500 uppercase">Axis</label>
                        <input type="number" value={axisOs} onChange={e => setAxisOs(Number(e.target.value))} className="w-full px-3 py-2 bg-slate-900 border border-slate-800 text-xs rounded-xl text-slate-300 focus:outline-none" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-semibold text-slate-500 uppercase">Add</label>
                        <input type="number" step="0.25" value={addOs} onChange={e => setAddOs(Number(e.target.value))} className="w-full px-3 py-2 bg-slate-900 border border-slate-800 text-xs rounded-xl text-slate-300 focus:outline-none" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* PD */}
                <div className="space-y-2 max-w-xs">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Pupillary Distance (PD)</label>
                  <input
                    type="number"
                    step="0.5"
                    value={pd}
                    onChange={(e) => setPd(Number(e.target.value))}
                    required
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-xl text-xs text-slate-300 focus:outline-none"
                  />
                  <span className="text-[10px] text-slate-600">Usually 54mm to 74mm</span>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold tracking-wide transition-all shadow-lg shadow-indigo-600/10"
                >
                  {loading ? 'Creating Order...' : 'Validate & Save Prescription'}
                </button>
              </form>
            )}
          </div>
        </div>

        {/* OCR Result Verify Side Panel */}
        <div className="space-y-6">
          {ocrResult && (
            <div className="glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-5">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-sm text-white">OCR Parsing Verification</h4>
                <span className="text-[9px] font-bold bg-amber-500/10 border border-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full uppercase tracking-wider">
                  Needs Audit
                </span>
              </div>
              
              <div className="p-3 bg-slate-950 border border-slate-900 rounded-xl space-y-2 text-xs">
                <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Raw Extracted Text</span>
                <p className="font-mono text-[10px] text-slate-400 line-clamp-3 leading-relaxed">{ocrResult.raw_text}</p>
              </div>

              {/* Edit parameters parsed */}
              <div className="space-y-3.5 border-t border-slate-900 pt-4">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Verify Extracted Parameters</span>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-[9px] font-semibold text-slate-500 uppercase">OD SPH</label>
                    <input type="number" step="0.25" value={sphOd} onChange={e => setSphOd(Number(e.target.value))} className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-800 text-[11px] rounded-lg text-slate-300" />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[9px] font-semibold text-slate-500 uppercase">OS SPH</label>
                    <input type="number" step="0.25" value={sphOs} onChange={e => setSphOs(Number(e.target.value))} className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-800 text-[11px] rounded-lg text-slate-300" />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[9px] font-semibold text-slate-500 uppercase">OD CYL</label>
                    <input type="number" step="0.25" value={cylOd} onChange={e => setCylOd(Number(e.target.value))} className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-800 text-[11px] rounded-lg text-slate-300" />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[9px] font-semibold text-slate-500 uppercase">OS CYL</label>
                    <input type="number" step="0.25" value={cylOs} onChange={e => setCylOs(Number(e.target.value))} className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-800 text-[11px] rounded-lg text-slate-300" />
                  </div>
                </div>
              </div>

              <button
                onClick={handleManualApprove}
                disabled={loading}
                className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold tracking-wide transition-all shadow-md shadow-emerald-950/20"
              >
                {loading ? 'Approving...' : 'Approve OCR Extraction'}
              </button>
            </div>
          )}

          {/* Similar historical configurations search */}
          <div className="glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-4">
            <h4 className="font-bold text-sm text-white">Semantic AI Suggestion</h4>
            
            {searchingSimilar ? (
              <div className="flex flex-col items-center justify-center py-6 space-y-2">
                <RefreshCw className="w-6 h-6 text-indigo-500 animate-spin" />
                <span className="text-[10px] text-slate-500">Searching similar lens prescriptions...</span>
              </div>
            ) : similarRx.length > 0 ? (
              <div className="space-y-3">
                <span className="text-[10px] font-semibold text-indigo-400 uppercase tracking-wider block">Nearest Neighbor Matches</span>
                {similarRx.map((rx, idx) => (
                  <div key={rx.prescription_id} className="p-3 bg-slate-900/40 border border-slate-800/40 rounded-xl space-y-2 text-[11px]">
                    <div className="flex items-center justify-between text-slate-300">
                      <span className="font-semibold">Prescription #{rx.prescription_id}</span>
                      <span className="text-[9px] font-bold text-indigo-400 font-mono">Similarity: {(rx.score * 100).toFixed(1)}%</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-slate-500">
                      <div>OD SPH: <span className="text-slate-300 font-semibold">{rx.sph_od}</span></div>
                      <div>OS SPH: <span className="text-slate-300 font-semibold">{rx.sph_os}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-slate-500 p-4 border border-dashed border-slate-900 rounded-xl text-xs leading-relaxed">
                Submit or digitize a prescription to query similar configuration recommendations dynamically.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
