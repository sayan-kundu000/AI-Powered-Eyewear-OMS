import React, { useState } from 'react'
import { MessageSquare, Send, RefreshCw, Database, Table } from 'lucide-react'

import { API_BASE_URL } from '../config'

interface Message {
  sender: 'user' | 'assistant';
  text: string;
  sql?: string;
  results?: any[];
}

export default function AIChatAssistant() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'assistant',
      text: "Hello! I am your AI-powered OMS assistant. Ask me to lookup orders, explain delays, or check store performance. E.g. 'Show orders from Bangalore' or 'Explain why order ORD-20260614-R1 is delayed'"
    }
  ])
  const [loading, setLoading] = useState(false)

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return
    
    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { sender: 'user', text: userMsg }])
    setLoading(true)

    const token = localStorage.getItem('token')
    try {
      const res = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ message: userMsg })
      })

      if (res.ok) {
        const data = await res.json()
        setMessages(prev => [...prev, {
          sender: 'assistant',
          text: data.response,
          sql: data.sql_query && data.sql_query !== "-- None --" ? data.sql_query : undefined,
          results: data.results && data.results.length > 0 ? data.results : undefined
        }])
      } else {
        const err = await res.json()
        setMessages(prev => [...prev, {
          sender: 'assistant',
          text: `Error: ${err.detail || "Unable to retrieve assistant response"}`
        }])
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        sender: 'assistant',
        text: "Error: Unable to connect to the assistant server."
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="glass-panel rounded-2xl border border-slate-900 shadow-xl overflow-hidden flex flex-col h-[calc(100vh-12rem)]">
      {/* Header */}
      <div className="p-4 bg-slate-950 border-b border-slate-900/60 flex items-center space-x-3">
        <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
          <MessageSquare className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <h3 className="font-bold text-sm text-white">Eyewear OMS Assistant</h3>
          <span className="text-[10px] text-slate-500">Natural Language SQL Generator & Delay Root Cause Expert</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 p-6 overflow-y-auto space-y-4">
        {messages.map((msg, index) => (
          <div key={index} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
            <div className={`max-w-xl rounded-2xl p-4 text-xs ${
              msg.sender === 'user' 
                ? 'bg-indigo-600 text-white rounded-br-none shadow-md shadow-indigo-950/20' 
                : 'bg-slate-900/80 text-slate-300 border border-slate-800/80 rounded-bl-none'
            }`}>
              <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>
              
              {/* SQL Panel */}
              {msg.sql && (
                <div className="mt-4 p-3 bg-slate-950 border border-slate-900/60 rounded-xl space-y-2 font-mono text-[10px]">
                  <div className="flex items-center space-x-1.5 text-indigo-400 font-semibold border-b border-slate-900 pb-1.5 uppercase tracking-wider text-[8px]">
                    <Database className="w-3 h-3" />
                    <span>Generated SQL Syntax</span>
                  </div>
                  <pre className="text-slate-400 overflow-x-auto select-all">{msg.sql}</pre>
                </div>
              )}

              {/* Data Table */}
              {msg.results && (
                <div className="mt-4 border border-slate-900/60 rounded-xl overflow-hidden">
                  <div className="px-3 py-2 bg-slate-950 border-b border-slate-900/60 flex items-center space-x-1.5 text-slate-400 font-semibold uppercase tracking-wider text-[8px]">
                    <Table className="w-3 h-3 text-indigo-400" />
                    <span>Query Outputs ({msg.results.length} rows)</span>
                  </div>
                  
                  <div className="overflow-x-auto text-[10px]">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-slate-950/60 border-b border-slate-900 text-slate-500 font-semibold">
                          {Object.keys(msg.results[0]).map((key) => (
                            <th key={key} className="px-3 py-2 uppercase tracking-wider text-[8px]">{key.replace(/_/g, ' ')}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-900">
                        {msg.results.map((row, rIdx) => (
                          <tr key={rIdx} className="hover:bg-slate-900/40">
                            {Object.values(row).map((val: any, cIdx) => (
                              <td key={cIdx} className="px-3 py-2 text-slate-300 font-medium">
                                {typeof val === 'number' && !Number.isInteger(val) ? val.toFixed(1) : String(val)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex items-center space-x-2 text-slate-500 pl-4 py-2">
            <RefreshCw className="w-4 h-4 animate-spin text-indigo-500" />
            <span className="text-[10px]">Analyzing metrics and generating parameters...</span>
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="p-4 bg-slate-950 border-t border-slate-900/60 flex items-center space-x-3 shrink-0">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question (e.g. 'Show progressive lens orders in bangalore')"
          className="flex-1 bg-slate-900/60 border border-slate-800 hover:border-slate-700 focus:border-indigo-500 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="p-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl transition-all shadow-md shadow-indigo-600/10"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  )
}
