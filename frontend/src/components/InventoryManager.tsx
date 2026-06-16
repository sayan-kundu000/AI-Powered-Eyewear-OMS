import React, { useEffect, useState } from 'react'
import { useOrderStore } from '../store/orderStore'
import { 
  Boxes, 
  TrendingUp, 
  Truck, 
  AlertTriangle, 
  RefreshCw, 
  Gauge, 
  Cpu,
  ChevronRight,
  TrendingDown,
  Layers,
  Ruler,
  Zap
} from 'lucide-react'

import { API_BASE_URL } from '../config'

export default function InventoryManager() {
  const { inventory, fetchInventory, addInventoryItem, addStockToItem } = useOrderStore()
  
  // States
  const [vendors, setVendors] = useState<any[]>([])
  const [loadingVendors, setLoadingVendors] = useState(false)
  const [selectedLens, setSelectedLens] = useState<any | null>(null)
  
  const [reorderPrediction, setReorderPrediction] = useState<any | null>(null)
  const [loadingPrediction, setLoadingPrediction] = useState(false)
  
  const [filterType, setFilterType] = useState('')
  const [lowStockOnly, setLowStockOnly] = useState(false)

  // Add inventory form states
  const [newType, setNewType] = useState('Single Vision')
  const [newIndex, setNewIndex] = useState(1.61)
  const [newCoating, setNewCoating] = useState('Anti-Reflective')
  const [newSph, setNewSph] = useState(0.00)
  const [newCyl, setNewCyl] = useState(0.00)
  const [newThickness, setNewThickness] = useState(2.2)
  const [newQuantity, setNewQuantity] = useState(25)
  const [formLoading, setFormLoading] = useState(false)

  useEffect(() => {
    fetchInventory()
    loadVendors()
  }, [])

  const handleQuickRestock = async (lensId: number, qty: number) => {
    try {
      const success = await addStockToItem(lensId, qty);
      if (success) {
        alert("Stock restocked (+10) successfully!");
      }
    } catch (err) {
      alert("Failed to restock stock.");
    }
  }

  const handleAddNewLens = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormLoading(true);
    try {
      const success = await addInventoryItem({
        lens_type: newType,
        index_value: Number(newIndex),
        coating: newCoating,
        power_sph: Number(newSph),
        power_cyl: Number(newCyl),
        thickness: Number(newThickness),
        quantity: Number(newQuantity)
      });
      if (success) {
        alert("Lens inventory blank added/restocked successfully!");
        // Reset some defaults
        setNewSph(0.00);
        setNewCyl(0.00);
        setNewQuantity(25);
      }
    } catch (err) {
      alert("Failed to add inventory item.");
    } finally {
      setFormLoading(false);
    }
  }


  const loadVendors = async () => {
    setLoadingVendors(true)
    const token = localStorage.getItem('token')
    try {
      const res = await fetch(`${API_BASE_URL}/inventory/vendor-recommendations`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setVendors(data)
      }
    } catch (error) {
      console.error("Failed to load vendors:", error)
    } finally {
      setLoadingVendors(false)
    }
  }

  const handlePredictReorder = async (lens: any) => {
    setSelectedLens(lens)
    setLoadingPrediction(true)
    setReorderPrediction(null)
    const token = localStorage.getItem('token')
    try {
      const res = await fetch(`${API_BASE_URL}/inventory/reorder-needs?lens_id=${lens.id}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (res.ok) {
        const data = await res.json()
        setReorderPrediction(data)
      } else {
        alert("Prediction failed.")
      }
    } catch (err) {
      alert("Network error running forecaster.")
    } finally {
      setLoadingPrediction(false)
    }
  }

  // Filter inventory logic
  const filteredInventory = inventory.filter((item) => {
    const matchesType = filterType ? item.lens_type === filterType : true
    const available = item.quantity - item.reserved_quantity
    const matchesLow = lowStockOnly ? available < 5 : true
    return matchesType && matchesLow
  })

  return (
    <div className="space-y-6">
      {/* Historical Stock Capability Profile */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="glass-panel p-5 rounded-2xl border border-slate-900 shadow-lg flex items-center justify-between">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">In-House Coatings Profile</span>
            <div className="flex flex-wrap gap-1 mt-1.5">
              {['Anti-Reflective', 'Blue Cut', 'Photochromic', 'Scratch-Resistant'].map((coat) => (
                <span key={coat} className="px-2 py-0.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-md text-[10px] font-medium">
                  {coat}
                </span>
              ))}
            </div>
          </div>
          <div className="p-3.5 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20 shrink-0">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-900 shadow-lg flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">In-House Thickness Range</span>
            <span className="text-2xl font-bold mt-1 block text-emerald-400 font-mono">1.5 mm - 3.2 mm</span>
            <span className="text-[10px] text-slate-500 block mt-1">Based on historical order analysis</span>
          </div>
          <div className="p-3.5 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20 shrink-0">
            <Ruler className="w-5 h-5" />
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-900 shadow-lg flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Express Delivery Capability</span>
            <span className="text-2xl font-bold mt-1 block text-amber-400">Power Auto-Check Enabled</span>
            <span className="text-[10px] text-slate-500 block mt-1">Instant dispatch check on client order placement</span>
          </div>
          <div className="p-3.5 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20 shrink-0">
            <Zap className="w-5 h-5" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Inventory Table */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 className="font-bold text-lg text-white">Lens Inventory Registry</h3>
              <p className="text-xs text-slate-500">Monitor lens blanks, reserves, and real-time stocks</p>
            </div>
            
            {/* Filter controls */}
            <div className="flex items-center space-x-3 text-xs">
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-300 focus:outline-none cursor-pointer"
              >
                <option value="">All Types</option>
                <option value="Single Vision">Single Vision</option>
                <option value="Progressive">Progressive</option>
                <option value="Blue Cut">Blue Cut</option>
              </select>

              <label className="flex items-center space-x-2 text-slate-400 font-semibold cursor-pointer">
                <input
                  type="checkbox"
                  checked={lowStockOnly}
                  onChange={(e) => setLowStockOnly(e.target.checked)}
                  className="rounded bg-slate-950 border-slate-850 text-indigo-600 focus:ring-0 focus:ring-offset-0"
                />
                <span>Low Stock (&lt; 5)</span>
              </label>
            </div>
          </div>

          <div className="overflow-x-auto max-h-[500px]">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-900 text-slate-500 font-semibold uppercase tracking-wider">
                  <th className="pb-3">Lens Spec</th>
                  <th className="pb-3">SPH/CYL</th>
                  <th className="pb-3">Coating</th>
                  <th className="pb-3">Thickness</th>
                  <th className="pb-3">In House</th>
                  <th className="pb-3">Reserved</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3 text-right">Replenish Tool</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-900/60">
                {filteredInventory.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-500 font-medium">
                      No stock matches criteria.
                    </td>
                  </tr>
                ) : (
                  filteredInventory.map((item) => {
                    const available = item.quantity - item.reserved_quantity
                    const isLow = available < 5
                    return (
                      <tr key={item.id} className="hover:bg-slate-900/20 transition-all">
                        <td className="py-3 font-semibold text-slate-200">
                          {item.lens_type} <span className="text-[10px] text-indigo-400">({item.index_value})</span>
                        </td>
                        <td className="py-3 text-slate-400 font-mono">
                          {item.power_sph >= 0 ? `+${item.power_sph.toFixed(2)}` : item.power_sph.toFixed(2)} / {item.power_cyl >= 0 ? `+${item.power_cyl.toFixed(2)}` : item.power_cyl.toFixed(2)}
                        </td>
                        <td className="py-3 text-slate-400">{item.coating}</td>
                        <td className="py-3 text-slate-400 font-mono">{item.thickness ? `${item.thickness.toFixed(1)} mm` : '2.2 mm'}</td>
                        <td className={`py-3 font-bold ${isLow ? 'text-rose-400' : 'text-slate-300'}`}>{item.quantity}</td>
                        <td className="py-3 text-slate-500 font-medium">{item.reserved_quantity}</td>
                        <td className="py-3">
                          <span className={`px-2 py-0.5 rounded text-[8px] font-bold tracking-wider uppercase border ${
                            item.status === 'IN_HOUSE' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                          }`}>
                            {item.status.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="py-3 text-right space-x-1.5 flex items-center justify-end">
                          <button
                            onClick={() => handleQuickRestock(item.id, 10)}
                            className="inline-flex items-center px-2 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 hover:text-white rounded-lg hover:border-emerald-500/50 transition-all font-semibold"
                            title="Quick restock 10 units"
                          >
                            <span>+10</span>
                          </button>
                          <button
                            onClick={() => handlePredictReorder(item)}
                            className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-slate-900 border border-slate-800 text-slate-300 hover:text-white rounded-lg hover:border-slate-700 transition-all font-semibold"
                          >
                            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                            <span>Analyze</span>
                          </button>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Prediction & Procurements Side Panel */}
        <div className="space-y-6">
          {/* Add New Lens Blank Form */}
          <div className="glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-4">
            <h4 className="font-bold text-sm text-white flex items-center space-x-2">
              <Boxes className="w-4 h-4 text-indigo-400" />
              <span>Add / Restock Lens Blank</span>
            </h4>
            <form onSubmit={handleAddNewLens} className="space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[10px] font-semibold text-slate-500 uppercase">Lens Type</label>
                  <select
                    value={newType}
                    onChange={(e) => setNewType(e.target.value)}
                    required
                    className="w-full px-2.5 py-2 bg-slate-950 border border-slate-800 focus:border-indigo-500 text-slate-300 rounded-xl focus:outline-none cursor-pointer"
                  >
                    <option value="Single Vision">Single Vision</option>
                    <option value="Progressive">Progressive</option>
                    <option value="Blue Cut">Blue Cut</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-semibold text-slate-500 uppercase">Index Value</label>
                  <select
                    value={newIndex}
                    onChange={(e) => setNewIndex(Number(e.target.value))}
                    required
                    className="w-full px-2.5 py-2 bg-slate-950 border border-slate-800 focus:border-indigo-500 text-slate-300 rounded-xl focus:outline-none cursor-pointer"
                  >
                    <option value={1.56}>1.56</option>
                    <option value={1.61}>1.61</option>
                    <option value={1.67}>1.67</option>
                    <option value={1.74}>1.74</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-semibold text-slate-500 uppercase">Coating</label>
                <select
                  value={newCoating}
                  onChange={(e) => setNewCoating(e.target.value)}
                  required
                  className="w-full px-2.5 py-2 bg-slate-950 border border-slate-800 focus:border-indigo-500 text-slate-300 rounded-xl focus:outline-none cursor-pointer"
                >
                  <option value="Anti-Reflective">Anti-Reflective Coating</option>
                  <option value="Blue Cut">Blue Cut / Digital Block</option>
                  <option value="Photochromic">Photochromic Transition</option>
                  <option value="Scratch-Resistant">Scratch-Resistant Shield</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[10px] font-semibold text-slate-500 uppercase">SPH Power</label>
                  <input
                    type="number"
                    step="0.25"
                    value={newSph}
                    onChange={(e) => setNewSph(Number(e.target.value))}
                    required
                    className="w-full px-2.5 py-2 bg-slate-950 border border-slate-800 focus:border-indigo-500 text-slate-300 rounded-xl focus:outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-semibold text-slate-500 uppercase">CYL Power</label>
                  <input
                    type="number"
                    step="0.25"
                    value={newCyl}
                    onChange={(e) => setNewCyl(Number(e.target.value))}
                    required
                    className="w-full px-2.5 py-2 bg-slate-950 border border-slate-800 focus:border-indigo-500 text-slate-300 rounded-xl focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[10px] font-semibold text-slate-500 uppercase">Thickness (mm)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={newThickness}
                    onChange={(e) => setNewThickness(Number(e.target.value))}
                    required
                    className="w-full px-2.5 py-2 bg-slate-950 border border-slate-800 focus:border-indigo-500 text-slate-300 rounded-xl focus:outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-semibold text-slate-500 uppercase">Quantity</label>
                  <input
                    type="number"
                    min="1"
                    value={newQuantity}
                    onChange={(e) => setNewQuantity(Number(e.target.value))}
                    required
                    className="w-full px-2.5 py-2 bg-slate-950 border border-slate-800 focus:border-indigo-500 text-slate-300 rounded-xl focus:outline-none"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={formLoading}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-xs font-bold tracking-wide text-white transition-all shadow-md shadow-indigo-950/20"
              >
                {formLoading ? 'Adding Lens...' : 'Add Stock / Register Blank'}
              </button>
            </form>
          </div>

          {/* Stock predictor */}
          <div className="glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-4">
            <h4 className="font-bold text-sm text-white flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-indigo-400 animate-pulse" />
              <span>Restock Forecaster</span>
            </h4>
            
            {loadingPrediction ? (
              <div className="flex flex-col items-center justify-center py-6 space-y-2">
                <RefreshCw className="w-6 h-6 text-indigo-500 animate-spin" />
                <span className="text-[10px] text-slate-500">Calculating replenishment quantities...</span>
              </div>
            ) : reorderPrediction ? (
              <div className="space-y-4">
                <div className="p-3 bg-slate-950 border border-slate-900 rounded-xl space-y-1 text-xs">
                  <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Target Item</span>
                  <span className="text-white font-bold block">{reorderPrediction.lens_type}</span>
                  <div className="flex justify-between mt-2 text-[10px] text-slate-400">
                    <span>In Stock: {reorderPrediction.current_quantity}</span>
                    <span>Reserved: {reorderPrediction.reserved_quantity}</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3.5 bg-slate-950 border border-slate-900 rounded-xl text-center">
                    <span className="text-[9px] font-semibold text-slate-500 uppercase tracking-wider block">Replenish Qty</span>
                    <span className="text-xl font-bold text-indigo-400 mt-1 block">
                      {reorderPrediction.forecasted_reorder.recommended_reorder_qty}
                    </span>
                    <span className="text-[8px] text-slate-500 mt-0.5 block">Estimated Units</span>
                  </div>

                  <div className="p-3.5 bg-slate-950 border border-slate-900 rounded-xl text-center">
                    <span className="text-[9px] font-semibold text-slate-500 uppercase tracking-wider block">Urgency Index</span>
                    <span className={`text-xl font-bold mt-1 block ${
                      reorderPrediction.forecasted_reorder.urgency_score > 60 ? 'text-rose-400' :
                      reorderPrediction.forecasted_reorder.urgency_score > 30 ? 'text-amber-400' :
                      'text-emerald-400'
                    }`}>
                      {reorderPrediction.forecasted_reorder.urgency_score}%
                    </span>
                    <span className="text-[8px] text-slate-500 mt-0.5 block">Priority Score</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center text-slate-500 p-4 border border-dashed border-slate-900 rounded-xl text-xs leading-relaxed">
                Select a specific lens record to prompt replenishment estimates.
              </div>
            )}
          </div>

          {/* Vendors */}
          <div className="glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-4">
            <h4 className="font-bold text-sm text-white flex items-center space-x-2">
              <Truck className="w-4 h-4 text-indigo-400" />
              <span>Multi-Factor Vendor Rankings</span>
            </h4>

            {loadingVendors ? (
              <div className="flex flex-col items-center justify-center py-6">
                <RefreshCw className="w-5 h-5 text-slate-500 animate-spin" />
              </div>
            ) : (
              <div className="space-y-3.5">
                {vendors.map((v, idx) => (
                  <div key={v.id} className="p-3.5 bg-slate-950 border border-slate-900/60 rounded-xl space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-200 truncate pr-2">{v.vendor_name}</span>
                      <span className="text-[10px] font-bold text-indigo-400 shrink-0 font-mono">#{idx+1} Score: {v.score}</span>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-500 border-t border-slate-900/60 pt-2">
                      <div>Reliability: <span className="text-slate-300 font-semibold">{v.reliability_score}%</span></div>
                      <div>Lead Time: <span className="text-slate-300 font-semibold">{v.sla_days} days</span></div>
                      <div>Cost Coeff: <span className="text-slate-300 font-semibold">₹{v.cost}</span></div>
                      <div>History Index: <span className="text-slate-300 font-semibold">{v.performance_history_score}%</span></div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
