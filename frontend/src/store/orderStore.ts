import { create } from 'zustand'

interface Order {
  id: number;
  order_number: string;
  customer_id: number;
  store_id: number;
  prescription_id: number | null;
  frame_id: number | null;
  lens_type: string;
  lens_index: number;
  coating_id: number | null;
  payment_status: string;
  total_amount: number;
  current_status: string;
  current_sla_days: number;
  remaining_tat_hours: number;
  breach_risk_prob: number;
  risk_score: string;
  lens_stock_status: string | null;
  delay_reason: string | null;
  created_at: string;
  updated_at: string;
}

interface DashboardOverview {
  total_active: number;
  completed: number;
  delayed: number;
  breached: number;
}

interface Analytics {
  overview: DashboardOverview;
  daily_orders: Array<{ date: string; orders: number }>;
  tat_trends: Array<{ lens_type: string; avg_tat_hours: number }>;
  qc_failure_rate: number;
  store_performance: Array<{ store_id: number; store_name: string; location: string; order_count: number; performance_score: number }>;
  lens_demand_heatmap: Array<any>;
}

interface OrderState {
  orders: Order[];
  analytics: Analytics | null;
  inventory: any[];
  notifications: any[];
  wsConnected: boolean;
  activeAlert: string | null;
  stores: any[];
  selectedOrderHistory: any[];
  
  fetchOrders: (search?: string, status?: string, storeId?: string, lensType?: string) => Promise<void>;
  fetchAnalytics: () => Promise<void>;
  fetchInventory: () => Promise<void>;
  fetchNotifications: () => Promise<void>;
  updateOrderStatus: (id: number, status: string, reason?: string) => Promise<void>;
  connectWebSocket: () => void;
  clearAlert: () => void;
  addInventoryItem: (item: any) => Promise<boolean>;
  addStockToItem: (lensId: number, quantity: number) => Promise<boolean>;
  fetchStores: () => Promise<void>;
  fetchOrderHistory: (orderId: number) => Promise<void>;
}

import { API_BASE_URL, WS_BASE_URL } from '../config'

export const useOrderStore = create<OrderState>((set, get) => {
  let ws: WebSocket | null = null;
  
  return {
    orders: [],
    analytics: null,
    inventory: [],
    notifications: [],
    wsConnected: false,
    activeAlert: null,
    stores: [],
    selectedOrderHistory: [],
    
    fetchOrders: async (search = "", status = "", storeId = "", lensType = "") => {
      const token = localStorage.getItem('token');
      if (!token) return;
      try {
        let url = `${API_BASE_URL}/orders?`;
        if (search) url += `search=${encodeURIComponent(search)}&`;
        if (status) url += `status=${encodeURIComponent(status)}&`;
        if (storeId) url += `store_id=${encodeURIComponent(storeId)}&`;
        if (lensType) url += `lens_type=${encodeURIComponent(lensType)}&`;
        
        const res = await fetch(url, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          set({ orders: data });
        }
      } catch (err) {
        console.error("Error fetching orders:", err);
      }
    },
    
    fetchStores: async () => {
      const token = localStorage.getItem('token');
      if (!token) return;
      try {
        const res = await fetch(`${API_BASE_URL}/orders/stores`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          set({ stores: data });
        }
      } catch (err) {
        console.error("Error fetching stores:", err);
      }
    },

    fetchOrderHistory: async (orderId: number) => {
      const token = localStorage.getItem('token');
      if (!token) return;
      try {
        const res = await fetch(`${API_BASE_URL}/orders/${orderId}/history`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          set({ selectedOrderHistory: data });
        }
      } catch (err) {
        console.error("Error fetching order history:", err);
      }
    },
    
    fetchAnalytics: async () => {
      const token = localStorage.getItem('token');
      if (!token) return;
      try {
        const res = await fetch(`${API_BASE_URL}/analytics/dashboard`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          set({ analytics: data });
        }
      } catch (err) {
        console.error("Error fetching analytics:", err);
      }
    },
    
    fetchInventory: async () => {
      const token = localStorage.getItem('token');
      if (!token) return;
      try {
        const res = await fetch(`${API_BASE_URL}/inventory`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          set({ inventory: data });
        }
      } catch (err) {
        console.error("Error fetching inventory:", err);
      }
    },
    
    fetchNotifications: async () => {
      const token = localStorage.getItem('token');
      if (!token) return;
      try {
        const res = await fetch(`${API_BASE_URL}/notifications`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          set({ notifications: data });
        }
      } catch (err) {
        console.error("Error fetching notifications:", err);
      }
    },
    
    updateOrderStatus: async (id: number, status: string, reason = "") => {
      const token = localStorage.getItem('token');
      if (!token) return;
      try {
        const res = await fetch(`${API_BASE_URL}/orders/${id}/status`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ status, reason })
        });
        if (res.ok) {
          await get().fetchOrders();
          await get().fetchAnalytics();
        }
      } catch (err) {
        console.error("Error updating status:", err);
      }
    },
    
    connectWebSocket: () => {
      if (ws) return; // already running
      
      ws = new WebSocket(WS_BASE_URL);
      
      ws.onopen = () => {
        set({ wsConnected: true });
        console.log("Real-time WebSockets synchronized.");
      };
      
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          console.log("WebSocket Broadcast received:", msg);
          
          if (msg.event) {
            let payloadObj = msg.payload;
            if (typeof payloadObj === 'string') {
              try {
                payloadObj = JSON.parse(payloadObj);
              } catch (e) {
                // Ignore parsing errors and keep string
              }
            }

            // Trigger alerts for breaches or updates
            let alertMsg = `Event: ${msg.event}`;
            if (payloadObj && typeof payloadObj === 'object') {
              if (payloadObj.message) {
                alertMsg = payloadObj.message;
              } else if (payloadObj.order_id) {
                alertMsg = `Order ID ${payloadObj.order_id} update: ${msg.event}`;
              }
            }
            set({ activeAlert: alertMsg });
            
            // Auto refresh state metrics
            get().fetchOrders();
            get().fetchAnalytics();
            get().fetchNotifications();
          }
        } catch (e) {
          // pong or checkalive messages
        }
      };
      
      ws.onclose = () => {
        set({ wsConnected: false });
        ws = null;
        console.log("WebSocket closed. Reconnecting in 5s...");
        setTimeout(() => get().connectWebSocket(), 5000);
      };
      
      ws.onerror = () => {
        set({ wsConnected: false });
      };
    },
    
    clearAlert: () => set({ activeAlert: null }),
    
    addInventoryItem: async (item: any) => {
      const token = localStorage.getItem('token');
      if (!token) return false;
      try {
        const res = await fetch(`${API_BASE_URL}/inventory`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify(item)
        });
        if (res.ok) {
          await get().fetchInventory();
          return true;
        } else {
          const err = await res.json();
          alert(err.detail || "Failed to add inventory item.");
          return false;
        }
      } catch (err) {
        console.error("Error adding inventory item:", err);
        return false;
      }
    },
    
    addStockToItem: async (lensId: number, quantity: number) => {
      const token = localStorage.getItem('token');
      if (!token) return false;
      try {
        const res = await fetch(`${API_BASE_URL}/inventory/${lensId}/add-stock`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ quantity })
        });
        if (res.ok) {
          await get().fetchInventory();
          return true;
        } else {
          const err = await res.json();
          alert(err.detail || "Failed to add stock.");
          return false;
        }
      } catch (err) {
        console.error("Error adding stock:", err);
        return false;
      }
    }
  }
})
