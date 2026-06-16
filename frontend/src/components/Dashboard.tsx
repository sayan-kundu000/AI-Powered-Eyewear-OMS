import React, { useEffect, useState } from 'react'
import { useOrderStore } from '../store/orderStore'
import { 
  Search, 
  Filter, 
  Activity, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  TrendingUp,
  Eye,
  ArrowRight,
  User,
  MapPin,
  Calendar,
  AlertCircle
} from 'lucide-react'

// Full list of status labels in order of logical progression
const FSM_STAGES = [
  "ORDER_PLACED",
  "PRESCRIPTION_RECEIVED",
  "PRESCRIPTION_VALIDATED",
  "FRAME_ALLOCATED",
  "LENS_ALLOCATED",
  "IN_LAB",
  "CUTTING",
  "COATING",
  "ASSEMBLY",
  "QC_PENDING",
  "PACKAGING",
  "SHIPPED",
  "OUT_FOR_DELIVERY",
  "DELIVERED"
]

const STAGE_COLORS: Record<string, string> = {
  ORDER_PLACED: "bg-blue-500/10 border-blue-500/20 text-blue-400",
  PRESCRIPTION_RECEIVED: "bg-cyan-500/10 border-cyan-500/20 text-cyan-400",
  PRESCRIPTION_VALIDATED: "bg-indigo-500/10 border-indigo-500/20 text-indigo-400",
  FRAME_ALLOCATED: "bg-purple-500/10 border-purple-500/20 text-purple-400",
  LENS_ALLOCATED: "bg-violet-500/10 border-violet-500/20 text-violet-400",
  IN_LAB: "bg-amber-500/10 border-amber-500/20 text-amber-400",
  CUTTING: "bg-orange-500/10 border-orange-500/20 text-orange-400",
  COATING: "bg-yellow-500/10 border-yellow-500/20 text-yellow-400",
  ASSEMBLY: "bg-lime-500/10 border-lime-500/20 text-lime-400",
  QC_PENDING: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400",
  QC_FAILED: "bg-red-500/10 border-red-500/20 text-red-400",
  REORDER: "bg-rose-500/10 border-rose-500/20 text-rose-400",
  PACKAGING: "bg-sky-500/10 border-sky-500/20 text-sky-400",
  SHIPPED: "bg-teal-500/10 border-teal-500/20 text-teal-400",
  OUT_FOR_DELIVERY: "bg-pink-500/10 border-pink-500/20 text-pink-400",
  DELIVERED: "bg-emerald-500/20 border-emerald-500/30 text-emerald-400",
  CANCELLED: "bg-slate-500/10 border-slate-500/20 text-slate-400",
}

export default function Dashboard() {
  const { 
    orders, 
    analytics, 
    stores, 
    selectedOrderHistory, 
    fetchOrders, 
    fetchAnalytics, 
    fetchStores, 
    fetchOrderHistory, 
    updateOrderStatus 
  } = useOrderStore()
  
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [lensTypeFilter, setLensTypeFilter] = useState('')
  const [storeFilter, setStoreFilter] = useState('')
  const [activeOnlyFilter, setActiveOnlyFilter] = useState(true)
  const [selectedOrder, setSelectedOrder] = useState<any | null>(null)
  
  // Transition fields
  const [transitionStatus, setTransitionStatus] = useState('')
  const [transitionReason, setTransitionReason] = useState('')
  const [transitionLoading, setTransitionLoading] = useState(false)

  // Fetch initial stores list once
  useEffect(() => {
    fetchStores()
  }, [])

  // Refetch orders when any filter values change
  useEffect(() => {
    fetchOrders(search, statusFilter, storeFilter, lensTypeFilter)
    fetchAnalytics()
  }, [search, statusFilter, storeFilter, lensTypeFilter])

  // Refetch order history logs when active selection changes
  useEffect(() => {
    if (selectedOrder) {
      fetchOrderHistory(selectedOrder.id)
    }
  }, [selectedOrder])

  // Get available next transitions based on VALID_TRANSITIONS
  const getNextTransitions = (currentStatus: string) => {
    // Standard mock transitions mapping matches VALID_TRANSITIONS in backend FSM service
    const transitions: Record<string, string[]> = {
      ORDER_PLACED: ["PRESCRIPTION_RECEIVED", "CANCELLED"],
      PRESCRIPTION_RECEIVED: ["PRESCRIPTION_VALIDATED", "CANCELLED"],
      PRESCRIPTION_VALIDATED: ["FRAME_ALLOCATED", "CANCELLED"],
      FRAME_ALLOCATED: ["LENS_ALLOCATED", "CANCELLED"],
      LENS_ALLOCATED: ["IN_LAB", "CANCELLED"],
      IN_LAB: ["CUTTING", "CANCELLED"],
      CUTTING: ["COATING", "CANCELLED"],
      COATING: ["ASSEMBLY", "CANCELLED"],
      ASSEMBLY: ["QC_PENDING", "CANCELLED"],
      QC_PENDING: ["QC_FAILED", "PACKAGING", "CANCELLED"],
      QC_FAILED: ["REORDER", "CANCELLED"],
      REORDER: ["PRESCRIPTION_VALIDATED", "CANCELLED"],
      PACKAGING: ["SHIPPED", "CANCELLED"],
      SHIPPED: ["OUT_FOR_DELIVERY", "CANCELLED"],
      OUT_FOR_DELIVERY: ["DELIVERED", "CANCELLED"],
      DELIVERED: [],
      CANCELLED: []
    }
    return transitions[currentStatus] || []
  }

  const handleTransition = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedOrder || !transitionStatus) return
    setTransitionLoading(true)
    try {
      await updateOrderStatus(selectedOrder.id, transitionStatus, transitionReason)
      
      // Explicitly refresh orders with current filters to maintain filter states
      await fetchOrders(search, statusFilter, storeFilter, lensTypeFilter)
      await fetchAnalytics()
      
      // Refresh selected order and history logs
      const refreshedOrders = useOrderStore.getState().orders
      const updated = refreshedOrders.find((o: any) => o.id === selectedOrder.id)
      setSelectedOrder(updated || null)
      if (updated) {
        await fetchOrderHistory(updated.id)
      }
      
      setTransitionStatus('')
      setTransitionReason('')
      alert("State transition applied successfully.")
    } catch (err) {
      alert("Error transitioning order status.")
    } finally {
      setTransitionLoading(false)
    }
  }

  const overview = analytics?.overview || { total_active: 0, completed: 0, delayed: 0, breached: 0 }

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="glass-panel p-5 rounded-2xl border border-slate-900 shadow-lg flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Active Orders</span>
            <span className="text-2xl font-bold mt-1 block">{overview.total_active}</span>
          </div>
          <div className="p-3.5 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
            <Activity className="w-5 h-5" />
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-900 shadow-lg flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Completed Today</span>
            <span className="text-2xl font-bold mt-1 block text-emerald-400">{overview.completed}</span>
          </div>
          <div className="p-3.5 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-900 shadow-lg flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Delayed Stage SLA</span>
            <span className="text-2xl font-bold mt-1 block text-amber-400">{overview.delayed}</span>
          </div>
          <div className="p-3.5 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-slate-900 shadow-lg flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Total SLA Breached</span>
            <span className="text-2xl font-bold mt-1 block text-rose-400">{overview.breached}</span>
          </div>
          <div className="p-3.5 bg-rose-500/10 text-rose-400 rounded-xl border border-rose-500/20">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Orders List Panel */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-900/60 pb-4">
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <h3 className="font-bold text-lg text-white">Production Order Tracking</h3>
              
              {/* Segmented Control Toggle for Active vs All Orders */}
              <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800/80 shrink-0">
                <button
                  type="button"
                  onClick={() => setActiveOnlyFilter(true)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    activeOnlyFilter 
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950/45' 
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Active ({orders.filter(o => o.current_status !== 'DELIVERED' && o.current_status !== 'CANCELLED').length})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveOnlyFilter(false)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    !activeOnlyFilter 
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950/45' 
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  All ({orders.length})
                </button>
              </div>
            </div>
            
            {/* Filter Inputs Group */}
            <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
              {/* Search */}
              <div className="relative flex-1 sm:flex-none">
                <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search order or client..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full sm:w-44 pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
                />
              </div>
              
              {/* Status Filter */}
              <div className="relative">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="pl-3 pr-8 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-indigo-500 appearance-none cursor-pointer"
                >
                  <option value="">All States</option>
                  {Object.keys(STAGE_COLORS).map(s => (
                    <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                  ))}
                </select>
                <Filter className="absolute right-3 top-2.5 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
              </div>

              {/* Lens Type Filter */}
              <div className="relative">
                <select
                  value={lensTypeFilter}
                  onChange={(e) => setLensTypeFilter(e.target.value)}
                  className="pl-3 pr-8 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-indigo-500 appearance-none cursor-pointer"
                >
                  <option value="">All Lenses</option>
                  <option value="Single Vision">Single Vision</option>
                  <option value="Progressive">Progressive</option>
                  <option value="Blue Cut">Blue Cut</option>
                </select>
                <Filter className="absolute right-3 top-2.5 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
              </div>

              {/* Store Filter */}
              <div className="relative">
                <select
                  value={storeFilter}
                  onChange={(e) => setStoreFilter(e.target.value)}
                  className="pl-3 pr-8 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-indigo-500 appearance-none cursor-pointer max-w-[130px] truncate"
                >
                  <option value="">All Stores</option>
                  {stores.map((s: any) => (
                    <option key={s.id} value={s.id}>{s.name} ({s.location})</option>
                  ))}
                </select>
                <MapPin className="absolute right-3 top-2.5 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
              </div>
            </div>
          </div>

          {/* Orders Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-900 text-slate-500">
                  <th className="pb-3 font-semibold uppercase tracking-wider">Order No</th>
                  <th className="pb-3 font-semibold uppercase tracking-wider">Lens Type</th>
                  <th className="pb-3 font-semibold uppercase tracking-wider">State</th>
                  <th className="pb-3 font-semibold uppercase tracking-wider">SLA Limit</th>
                  <th className="pb-3 font-semibold uppercase tracking-wider">Risk Index</th>
                  <th className="pb-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-900/60">
                {(() => {
                  const displayedOrders = activeOnlyFilter
                    ? orders.filter(o => o.current_status !== 'DELIVERED' && o.current_status !== 'CANCELLED')
                    : orders;
                    
                  if (displayedOrders.length === 0) {
                    return (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-slate-500 font-medium">
                          No active orders matched criteria.
                        </td>
                      </tr>
                    );
                  }
                  
                  return displayedOrders.map((o) => (
                    <tr key={o.id} className="hover:bg-slate-900/20 transition-all">
                      <td className="py-3.5 font-semibold text-slate-200">
                        {o.order_number}
                      </td>
                      <td className="py-3.5 text-slate-400 flex items-center flex-wrap gap-1">
                        <span>{o.lens_type}</span>
                        <span className="text-[10px] text-slate-600">index {o.lens_index}</span>
                        {o.lens_stock_status === 'IN_HOUSE' && (
                          <span className="text-[8px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.2 rounded font-bold uppercase shrink-0">In-House</span>
                        )}
                        {o.lens_stock_status === 'VENDOR_REQUIRED' && (
                          <span className="text-[8px] text-amber-400 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.2 rounded font-bold uppercase shrink-0">Vendor</span>
                        )}
                      </td>
                      <td className="py-3.5">
                        <span className={`px-2 py-0.5 border rounded-full text-[9px] font-bold tracking-wide uppercase ${STAGE_COLORS[o.current_status] || 'bg-slate-500/10 text-slate-400 border-slate-500/20'}`}>
                          {o.current_status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className={`py-3.5 font-medium ${o.remaining_tat_hours < 0 ? 'text-rose-400' : 'text-slate-400'}`}>
                        {o.remaining_tat_hours < 0 ? (
                          <div className="flex items-center space-x-1 text-rose-400">
                            <AlertTriangle className="w-3.5 h-3.5 text-rose-400 animate-pulse shrink-0" />
                            <span className="font-bold">Breached ({Math.abs(o.remaining_tat_hours).toFixed(1)}h)</span>
                          </div>
                        ) : (
                          <span>{o.remaining_tat_hours.toFixed(1)}h left</span>
                        )}
                      </td>
                      <td className="py-3.5 font-medium">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          o.risk_score === 'High' ? 'bg-rose-500/10 text-rose-400' : 
                          o.risk_score === 'Medium' ? 'bg-amber-500/10 text-amber-400' : 
                          'bg-emerald-500/10 text-emerald-400'
                        }`}>
                          {o.risk_score}
                        </span>
                      </td>
                      <td className="py-3.5 text-right">
                        <button
                          onClick={() => setSelectedOrder(o)}
                          className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-slate-900 border border-slate-800 text-slate-300 hover:text-white rounded-lg hover:border-slate-700 transition-all font-semibold"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Audit</span>
                        </button>
                      </td>
                    </tr>
                  ))
                })()}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Order Detail Panel */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-900 shadow-lg space-y-6">
          <h3 className="font-bold text-lg text-white">Order Control Hub</h3>
          
          {selectedOrder ? (
            <div className="space-y-6">
              {/* Order Identity Card */}
              <div className="p-4 bg-slate-950 border border-slate-900 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-base font-bold text-white">{selectedOrder.order_number}</span>
                  <span className={`text-[9px] font-bold border px-2 py-0.5 rounded-full uppercase tracking-wide ${STAGE_COLORS[selectedOrder.current_status]}`}>
                    {selectedOrder.current_status.replace(/_/g, ' ')}
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-900/60 text-xs">
                  <div>
                    <span className="text-slate-500 block uppercase font-semibold text-[9px] tracking-wider">Store ID</span>
                    <span className="text-slate-300 font-medium">Store #{selectedOrder.store_id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block uppercase font-semibold text-[9px] tracking-wider">Client ID</span>
                    <span className="text-slate-300 font-medium">Client #{selectedOrder.customer_id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block uppercase font-semibold text-[9px] tracking-wider">Amount</span>
                    <span className="text-slate-300 font-medium">₹{selectedOrder.total_amount.toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block uppercase font-semibold text-[9px] tracking-wider">Payment Status</span>
                    <span className={`font-semibold ${selectedOrder.payment_status === 'PAID' ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {selectedOrder.payment_status}
                    </span>
                  </div>
                </div>
                
                {/* Lens Stock Availability Status */}
                <div className="pt-3 border-t border-slate-900/60 mt-3 space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500 font-semibold uppercase text-[9px] tracking-wider">Lens Stock Status</span>
                    <span className={`font-bold uppercase text-[9px] ${
                      selectedOrder.lens_stock_status === 'IN_HOUSE' ? 'text-emerald-400' :
                      selectedOrder.lens_stock_status === 'VENDOR_REQUIRED' ? 'text-amber-400' :
                      'text-slate-400'
                    }`}>
                      {selectedOrder.lens_stock_status === 'IN_HOUSE' ? 'In-House (Express)' :
                       selectedOrder.lens_stock_status === 'VENDOR_REQUIRED' ? 'Procurement Required' :
                       selectedOrder.lens_stock_status || 'Pending Verification'}
                    </span>
                  </div>

                  {selectedOrder.lens_stock_status === 'VENDOR_REQUIRED' && (
                    <div className="p-3 bg-amber-500/5 border border-amber-500/10 rounded-xl space-y-1.5 mt-2 text-[10px] text-slate-400">
                      <div className="text-amber-400 font-bold uppercase tracking-wider text-[8px] flex items-center space-x-1">
                        <AlertTriangle className="w-3 h-3" />
                        <span>Recommended Sourcing Vendor</span>
                      </div>
                      <div className="flex justify-between text-slate-300 font-semibold">
                        <span>Essilor India Manufacturing</span>
                        <span className="text-indigo-400">Score: 82.5</span>
                      </div>
                      <div className="flex justify-between text-[9px] text-slate-500">
                        <span>Lead Time: 3 Days</span>
                        <span>Est Price: ₹450</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* SLA Breach Warning Alert */}
              {selectedOrder.remaining_tat_hours < 0 && (
                <div className="p-3.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-xs flex flex-col space-y-3 shadow-sm">
                  <div className="flex items-start space-x-2">
                    <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-rose-400 animate-pulse" />
                    <div>
                      <span className="font-bold uppercase tracking-wider text-[9px] text-rose-400 block mb-0.5">SLA Breach Warning</span>
                      <p className="text-slate-300 leading-normal font-medium">
                        This order has breached its SLA limit by {Math.abs(selectedOrder.remaining_tat_hours).toFixed(1)} hours. Urgent attention is required!
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={async (e) => {
                      const btn = e.currentTarget;
                      const originalText = btn.innerText;
                      try {
                        btn.disabled = true;
                        btn.innerText = "Sending Alert Email...";
                        const token = localStorage.getItem('token');
                        const res = await fetch(`${window.location.origin}/api/v1/predictions/check-sla-breach/${selectedOrder.id}`, {
                          method: 'POST',
                          headers: { 'Authorization': `Bearer ${token}` }
                        });
                        if (res.ok) {
                          alert(`SLA Breach alert email successfully sent for Order ${selectedOrder.order_number}!`);
                        } else {
                          const data = await res.json();
                          alert(data.detail || "Failed to trigger breach alert email.");
                        }
                      } catch (err) {
                        alert("Network error: failed to trigger breach alert email.");
                      } finally {
                        btn.disabled = false;
                        btn.innerText = originalText;
                      }
                    }}
                    className="w-full py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg font-bold text-xs transition-all shadow-md shadow-rose-950/20 hover:scale-[1.01]"
                  >
                    Send SLA Breach Alert Email
                  </button>
                </div>
              )}

              {/* Latest Status Notes */}
              {selectedOrder.delay_reason && (
                <div className="p-3.5 bg-indigo-500/5 border border-indigo-500/15 rounded-xl text-xs space-y-1">
                  <span className="font-bold uppercase tracking-wider text-[9px] text-indigo-400 block">Latest Status Notes</span>
                  <p className="text-slate-300 leading-normal font-medium">{selectedOrder.delay_reason}</p>
                </div>
              )}

              {/* FSM Stage Progress map */}
              <div>
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-3">State Timeline</span>
                <div className="relative pl-5 space-y-3.5 before:content-[''] before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-[1px] before:bg-slate-900">
                  {/* Current State Indicator */}
                  <div className="relative flex items-center space-x-3 text-xs">
                    <span className="absolute -left-[18px] w-2.5 h-2.5 rounded-full bg-indigo-500 ring-4 ring-indigo-950/40" />
                    <div>
                      <span className="font-semibold text-slate-200 uppercase">{selectedOrder.current_status.replace(/_/g, ' ')}</span>
                      <span className="text-[10px] text-slate-500 block">Current Stage</span>
                    </div>
                  </div>
                  
                  {/* Next Available Transitions */}
                  {getNextTransitions(selectedOrder.current_status).map((t, idx) => (
                    <div key={t} className="relative flex items-center space-x-3 text-xs opacity-60">
                      <span className="absolute -left-[18px] w-2.5 h-2.5 rounded-full bg-slate-800" />
                      <div>
                        <span className="font-medium text-slate-400 uppercase">{t.replace(/_/g, ' ')}</span>
                        {idx === 0 && <span className="text-[9px] text-indigo-400 block font-semibold">Recommended Progression</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Transition History Logs Timeline */}
              {selectedOrderHistory && selectedOrderHistory.length > 0 && (
                <div className="border-t border-slate-900/60 pt-5 space-y-3">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Transition History Logs</span>
                  <div className="relative pl-5 space-y-4 before:content-[''] before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-[1px] before:bg-slate-900">
                    {selectedOrderHistory.map((h: any) => (
                      <div key={h.id} className="relative text-xs space-y-1">
                        <span className="absolute -left-[18px] top-1.5 w-2 h-2 rounded-full bg-slate-950 border border-indigo-500/40" />
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-300 uppercase tracking-wide">
                            {h.new_status ? h.new_status.replace(/_/g, ' ') : h.action}
                          </span>
                          <span className="text-[9px] text-slate-500">
                            {new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <div className="text-[10px] text-slate-500 flex flex-wrap justify-between gap-1">
                          <span>By: {h.user_name}</span>
                          <span>{new Date(h.timestamp).toLocaleDateString()}</span>
                        </div>
                        {h.reason && (
                          <div className="mt-1 p-2 bg-slate-900/40 border border-slate-900 rounded-lg text-[10px] text-indigo-300 leading-normal">
                            <span className="font-bold text-[8px] uppercase tracking-wider block text-slate-500 mb-0.5">Logged Reason</span>
                            {h.reason}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* State Transition Form */}
              {getNextTransitions(selectedOrder.current_status).length > 0 ? (
                <form onSubmit={handleTransition} className="space-y-4 border-t border-slate-900/60 pt-5">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Transition Status To</label>
                    <select
                      value={transitionStatus}
                      onChange={(e) => setTransitionStatus(e.target.value)}
                      required
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-800 focus:border-indigo-500 text-slate-300 rounded-xl text-xs focus:outline-none cursor-pointer"
                    >
                      <option value="">-- Select Target State --</option>
                      {getNextTransitions(selectedOrder.current_status).map((t) => (
                        <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                      Transition Reason / Notes {selectedOrder.remaining_tat_hours < 0 && <span className="text-rose-400 font-bold">* (Required for Delay)</span>}
                    </label>
                    <textarea
                      value={transitionReason}
                      onChange={(e) => setTransitionReason(e.target.value)}
                      rows={2}
                      required={selectedOrder.remaining_tat_hours < 0}
                      placeholder={selectedOrder.remaining_tat_hours < 0 ? "Log details/reason for this delay (Required)..." : "Input details/notes for logs..."}
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-800 focus:border-indigo-500 text-slate-300 rounded-xl text-xs focus:outline-none resize-none"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={transitionLoading || !transitionStatus}
                    className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-xs font-bold tracking-wide text-white transition-all disabled:opacity-50"
                  >
                    {transitionLoading ? 'Applying Transition...' : 'Execute State Transition'}
                  </button>
                </form>
              ) : (
                <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl text-xs text-center flex items-center justify-center space-x-2">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Order is fully processed. No further actions required.</span>
                </div>
              )}
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-center text-slate-500 p-4 border border-dashed border-slate-900 rounded-2xl">
              <AlertCircle className="w-8 h-8 text-slate-600 mb-3 animate-pulse" />
              <p className="text-xs max-w-[180px] font-medium leading-relaxed">
                Select an active order from the production list to inspect the timeline and execute state transitions.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
