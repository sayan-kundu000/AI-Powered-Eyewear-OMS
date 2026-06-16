export const API_BASE_URL = (import.meta.env.VITE_API_URL || window.location.origin) + "/api/v1";
export const WS_BASE_URL = (import.meta.env.VITE_WS_URL || 
  ((window.location.protocol === "https:" ? "wss://" : "ws://") + window.location.host)) + "/ws/dashboard";
