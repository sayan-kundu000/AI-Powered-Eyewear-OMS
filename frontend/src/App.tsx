import React, { useEffect, useState } from 'react'
import { useAuthStore } from './store/authStore'
import { useOrderStore } from './store/orderStore'
import Dashboard from './components/Dashboard'
import PrescriptionUpload from './components/PrescriptionUpload'
import QCVisionVerify from './components/QCVisionVerify'
import InventoryManager from './components/InventoryManager'
import AIChatAssistant from './components/AIChatAssistant'
import AnalyticsView from './components/AnalyticsView'
import SupplyChainGraph from './components/SupplyChainGraph'
import { 
  LayoutDashboard, 
  FileText, 
  Scan, 
  Boxes, 
  MessageSquareCode, 
  BarChart3, 
  Network, 
  LogOut, 
  User as UserIcon, 
  Lock, 
  Mail, 
  Bell, 
  RefreshCw,
  ShieldCheck
} from 'lucide-react'

import { API_BASE_URL } from './config'

export default function App() {
  const { token, user, isAuthenticated, isLoading, error, login, logout, setUser, setError, setLoading } = useAuthStore()
  const { wsConnected, activeAlert, clearAlert, connectWebSocket } = useOrderStore()
  const [activeTab, setActiveTab] = useState('dashboard')
  const [theme, setTheme] = useState<'dark' | 'light' | 'neon'>(
    (localStorage.getItem('theme') as 'dark' | 'light' | 'neon') || 'light'
  )
  
  const handleSetTheme = (newTheme: 'dark' | 'light' | 'neon') => {
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
  }
  
  // Login fields
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  
  // Register fields
  const [isRegistering, setIsRegistering] = useState(false)
  const [fullName, setFullName] = useState('')
  const [selectedRole, setSelectedRole] = useState('CUSTOMER')

  // Check login on load
  useEffect(() => {
    const checkUser = async () => {
      if (!token) return
      setLoading(true)
      try {
        const res = await fetch(`${API_BASE_URL}/auth/me`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        if (res.ok) {
          const userData = await res.json()
          setUser(userData)
        } else {
          logout()
        }
      } catch (err) {
        console.error("Auth check failed:", err)
        logout()
      } finally {
        setLoading(false)
      }
    }
    checkUser()
  }, [token])

  // Connect websocket on auth success
  useEffect(() => {
    if (isAuthenticated) {
      connectWebSocket()
    }
  }, [isAuthenticated])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const formData = new URLSearchParams()
      formData.append('username', email)
      formData.append('password', password)

      const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
      })
      
      if (res.ok) {
        const data = await res.json()
        login(data.access_token)
      } else {
        const data = await res.json()
        setError(data.detail || "Authentication failed")
      }
    } catch (err) {
      setError("Network error. Make sure the backend is running.")
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: fullName, role: selectedRole })
      })
      if (res.ok) {
        setIsRegistering(false)
        setPassword('')
        alert("Registration successful! Please login.")
      } else {
        const data = await res.json()
        setError(data.detail || "Registration failed")
      }
    } catch (err) {
      setError("Network error. Make sure the backend is running.")
    } finally {
      setLoading(false)
    }
  }

  if (isLoading && !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#090d16] text-[#e2e8f0]">
        <div className="flex flex-col items-center space-y-4">
          <RefreshCw className="w-12 h-12 text-indigo-500 animate-spin" />
          <p className="text-sm tracking-wider text-slate-400">Loading Eyewear OMS Platform...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#090d16] text-[#e2e8f0] px-4">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(99,102,241,0.15),transparent_60%)] pointer-events-none" />
        
        <div className="w-full max-w-md glass-panel p-8 rounded-2xl border border-slate-800 shadow-2xl relative z-10">
          <div className="text-center mb-8">
            <div className="inline-flex p-3 bg-indigo-500/10 rounded-xl mb-3 border border-indigo-500/20">
              <ShieldCheck className="w-8 h-8 text-indigo-400" />
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-indigo-200 to-indigo-400 bg-clip-text text-transparent">
              Eyewear OMS
            </h1>
            <p className="text-xs text-slate-400 mt-1 uppercase tracking-widest">
              AI-Powered Order Management System
            </p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 text-red-200 rounded-xl text-sm text-center">
              {error}
            </div>
          )}

          <form onSubmit={isRegistering ? handleRegister : handleLogin} className="space-y-5">
            {isRegistering && (
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Full Name</label>
                <div className="relative">
                  <UserIcon className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                  <input 
                    type="text" 
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    placeholder="Enter your full name"
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-900/60 border border-slate-800 focus:border-indigo-500 rounded-xl text-slate-200 focus:outline-none transition-colors"
                  />
                </div>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="name@company.com"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-900/60 border border-slate-800 focus:border-indigo-500 rounded-xl text-slate-200 focus:outline-none transition-colors"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 w-5 h-5 text-slate-500" />
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-900/60 border border-slate-800 focus:border-indigo-500 rounded-xl text-slate-200 focus:outline-none transition-colors"
                />
              </div>
            </div>

            <button 
              type="submit" 
              className="w-full py-3 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 rounded-xl text-sm font-semibold tracking-wide shadow-lg shadow-indigo-600/20 text-white transition-all transform hover:-translate-y-0.5 active:translate-y-0"
            >
              {isRegistering ? 'Create Account' : 'Sign In'}
            </button>
          </form>

          <div className="text-center mt-6">
            <button 
              type="button" 
              onClick={() => {
                setIsRegistering(!isRegistering);
                setError(null);
              }}
              className="text-xs font-medium text-indigo-400 hover:underline"
            >
              {isRegistering ? 'Already have an account? Sign In' : "Don't have an account? Register"}
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Define sidebar navigation items based on user roles
  const userRoles = user?.roles || []
  const isAdminOrStaff = userRoles.includes('ADMIN') || userRoles.includes('STORE_STAFF')
  const isAdminOrLab = userRoles.includes('ADMIN') || userRoles.includes('LAB_TECH')

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, show: true },
    { id: 'prescription', label: 'Prescription OCR', icon: FileText, show: isAdminOrStaff },
    { id: 'qc', label: 'QC Lab Verification', icon: Scan, show: isAdminOrLab },
    { id: 'inventory', label: 'Inventory & Forecast', icon: Boxes, show: true },
    { id: 'analytics', label: 'Performance Analytics', icon: BarChart3, show: true },
    { id: 'supply', label: 'Supply Chain Graph', icon: Network, show: true },
    { id: 'chat', label: 'AI OMS Assistant', icon: MessageSquareCode, show: isAdminOrStaff }
  ]

  return (
    <div className={`theme-${theme} min-h-screen flex bg-[#070b13] text-[#e2e8f0] transition-colors duration-300 w-full`}>
      {/* Sidebar */}
      <aside className="w-64 glass-panel border-r border-slate-900 flex flex-col justify-between py-6 px-4 shrink-0">
        <div>
          {/* Logo */}
          <div className="flex items-center space-x-3 px-2 mb-8">
            <div className="p-2 bg-gradient-to-tr from-indigo-500 to-violet-500 rounded-lg">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="font-bold text-lg leading-tight bg-gradient-to-r from-white via-indigo-100 to-indigo-300 bg-clip-text text-transparent">
                Eyewear OMS
              </h2>
              <span className="text-[10px] text-slate-500 tracking-wider uppercase block">Enterprise AI</span>
            </div>
          </div>

          {/* Navigation */}
          <nav className="space-y-1.5">
            {navItems.filter(item => item.show).map((item) => {
              const Icon = item.icon
              const active = activeTab === item.id
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center space-x-3 px-3.5 py-3 rounded-xl text-sm font-medium transition-all ${
                    active 
                      ? 'bg-gradient-to-r from-indigo-600/20 to-violet-600/10 text-indigo-300 border-l-2 border-indigo-500 shadow-md shadow-indigo-950/20' 
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
                  }`}
                >
                  <Icon className={`w-5 h-5 ${active ? 'text-indigo-400' : 'text-slate-500'}`} />
                  <span>{item.label}</span>
                </button>
              )
            })}
          </nav>
        </div>

        {/* User Card */}
        <div className="pt-6 border-t border-slate-900">
          <div className="flex items-center space-x-3 p-2 bg-slate-900/40 rounded-xl mb-4 border border-slate-800/40">
            <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold uppercase">
              {user?.full_name?.substring(0, 2)}
            </div>
            <div className="overflow-hidden">
              <h4 className="text-xs font-semibold text-slate-200 truncate">{user?.full_name}</h4>
              <p className="text-[10px] text-slate-500 truncate">{user?.email}</p>
              <div className="flex flex-wrap gap-1 mt-1">
                {user?.roles?.map((role) => (
                  <span key={role} className="text-[8px] font-bold bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 px-1 py-0.2 rounded uppercase tracking-wider">
                    {role}
                  </span>
                ))}
              </div>
            </div>
          </div>
          
          <button
            onClick={() => logout()}
            className="w-full flex items-center justify-center space-x-2 py-2.5 rounded-xl text-xs font-semibold text-red-400 hover:text-red-300 hover:bg-red-500/5 border border-red-500/10 hover:border-red-500/20 transition-all"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Header */}
        <header className="h-16 glass-panel border-b border-slate-900 flex items-center justify-between px-8 shrink-0 relative z-20">
          <div className="flex items-center space-x-4">
            <h1 className="text-xl font-bold tracking-tight text-white capitalize">{activeTab}</h1>
            <div className="flex items-center space-x-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] px-2 py-0.5 rounded-full font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>API Gateway Connected</span>
            </div>
            {wsConnected && (
              <div className="flex items-center space-x-2 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] px-2 py-0.5 rounded-full font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                <span>WebSockets Active</span>
              </div>
            )}
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Theme Switcher Segmented Control */}
            <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800/80 mr-2 shrink-0">
              <button
                type="button"
                onClick={() => handleSetTheme('light')}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  theme === 'light'
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-950/45'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Light
              </button>
              <button
                type="button"
                onClick={() => handleSetTheme('neon')}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  theme === 'neon'
                    ? 'bg-emerald-600 text-[#02140c] shadow-md shadow-emerald-950/45'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Neon Green
              </button>
              <button
                type="button"
                onClick={() => handleSetTheme('dark')}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  theme === 'dark'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950/45'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Dark
              </button>
            </div>

            {/* Notifications Panel */}
            <div className="relative">
              <button className="p-2 bg-slate-900/60 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white rounded-xl transition-all relative">
                <Bell className="w-4 h-4" />
                {activeAlert && (
                  <span className="absolute top-1 right-1 w-2.5 h-2.5 rounded-full bg-indigo-500 border border-[#070b13] animate-ping" />
                )}
              </button>
            </div>
          </div>
        </header>

        {/* Dashboard WebSocket Notifications banner */}
        {activeAlert && (
          <div className="mx-8 mt-6 p-4 bg-gradient-to-r from-indigo-900/40 via-violet-900/20 to-slate-900/40 border-l-4 border-indigo-500 text-slate-300 rounded-r-xl flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Bell className="w-5 h-5 text-indigo-400 animate-bounce" />
              <div>
                <span className="font-semibold text-indigo-300 block text-xs uppercase tracking-wider">Real-time Notification</span>
                <span className="text-sm">{activeAlert}</span>
              </div>
            </div>
            <button 
              onClick={() => clearAlert()} 
              className="text-xs font-semibold text-slate-500 hover:text-slate-300 hover:underline px-3 py-1 bg-slate-900/80 rounded-lg border border-slate-800"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Content Body */}
        <main className="flex-1 p-8 relative">
          {activeTab === 'dashboard' && <Dashboard />}
          {activeTab === 'prescription' && <PrescriptionUpload />}
          {activeTab === 'qc' && <QCVisionVerify />}
          {activeTab === 'inventory' && <InventoryManager />}
          {activeTab === 'chat' && <AIChatAssistant />}
          {activeTab === 'analytics' && <AnalyticsView />}
          {activeTab === 'supply' && <SupplyChainGraph />}
        </main>
      </div>
    </div>
  )
}
