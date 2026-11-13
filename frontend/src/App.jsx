import React, { useState } from 'react';
import axios from 'axios';
import { Shield, Send, LogOut, User, Lock, AlertCircle } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [userProfile, setUserProfile] = useState(
    JSON.parse(localStorage.getItem("userProfile") || "null")
  );

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [loadingAuth, setLoadingAuth] = useState(false);

  const [messages, setMessages] = useState([]);
  const [inputQuery, setInputQuery] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthError("");
    setLoadingAuth(true);

    try {
      const res = await axios.post(`${API_BASE}/auth/login`, {
        username: username.trim(),
        password: password.trim()
      });

      const data = res.data;
      setToken(data.access_token);
      const profile = {
        username: username,
        role: data.role,
        allowed_departments: data.allowed_departments
      };
      setUserProfile(profile);

      localStorage.setItem("token", data.access_token);
      localStorage.setItem("userProfile", JSON.stringify(profile));
    } catch (err) {
      setAuthError(err.response?.data?.detail || "Invalid username or password");
    } finally {
      setLoadingAuth(false);
    }
  };

  const handleLogout = () => {
    setToken("");
    setUserProfile(null);
    setMessages([]);
    localStorage.removeItem("token");
    localStorage.removeItem("userProfile");
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputQuery.trim() || chatLoading) return;

    const userMessage = { sender: "user", text: inputQuery };
    setMessages((prev) => [...prev, userMessage]);
    const currentQuery = inputQuery;
    setInputQuery("");
    setChatLoading(true);

    try {
      const res = await axios.post(
        `${API_BASE}/v1/chat`,
        { query: currentQuery },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const botMessage = {
        sender: "bot",
        text: res.data.answer,
        status: res.data.status,
        latency: res.data.latency_seconds,
        tokens: res.data.token_usage,
        sources: res.data.sources || []
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      if (err.response?.status === 401) {
        handleLogout();
        alert("Session expired or invalid token. Please log in again.");
      } else {
        setMessages((prev) => [
          ...prev,
          {
            sender: "bot",
            text: "Backend API connection failed. Check if FastAPI server is running.",
            status: "ERROR",
            sources: []
          }
        ]);
      }
    } finally {
      setChatLoading(false);
    }
  };

  if (!token || !userProfile) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", width: "100%" }}>
        <div style={{ background: "#1e293b", padding: "35px", borderRadius: "12px", width: "380px", border: "1px solid #334155" }}>
          <div style={{ textAlign: "center", marginBottom: "25px" }}>
            <Shield size={42} color="#38bdf8" style={{ marginBottom: "10px" }} />
            <h2 style={{ fontSize: "22px", fontWeight: "600" }}>FinSolve Enterprise RAG</h2>
            <p style={{ fontSize: "13px", color: "#94a3b8" }}>Sign in with enterprise credentials</p>
          </div>

          {authError && (
            <div style={{ background: "rgba(239, 68, 68, 0.15)", border: "1px solid #ef4444", color: "#fca5a5", padding: "10px", borderRadius: "6px", marginBottom: "15px", fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
              <AlertCircle size={16} /> {authError}
            </div>
          )}

          <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
            <div>
              <label style={{ fontSize: "12px", color: "#cbd5e1" }}>Username</label>
              <div style={{ display: "flex", alignItems: "center", background: "#0f172a", border: "1px solid #475569", borderRadius: "6px", padding: "8px 12px", marginTop: "4px" }}>
                <User size={16} color="#94a3b8" style={{ marginRight: "8px" }} />
                <input
                  type="text"
                  placeholder="alice / bob / admin"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  style={{ background: "transparent", border: "none", color: "#fff", outline: "none", width: "100%" }}
                />
              </div>
            </div>

            <div>
              <label style={{ fontSize: "12px", color: "#cbd5e1" }}>Password</label>
              <div style={{ display: "flex", alignItems: "center", background: "#0f172a", border: "1px solid #475569", borderRadius: "6px", padding: "8px 12px", marginTop: "4px" }}>
                <Lock size={16} color="#94a3b8" style={{ marginRight: "8px" }} />
                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  style={{ background: "transparent", border: "none", color: "#fff", outline: "none", width: "100%" }}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loadingAuth}
              style={{ background: "#2563eb", color: "#fff", padding: "10px", border: "none", borderRadius: "6px", fontWeight: "600", cursor: "pointer", marginTop: "10px" }}
            >
              {loadingAuth ? "Verifying..." : "Sign In"}
            </button>
          </form>

          <div style={{ marginTop: "20px", fontSize: "11px", color: "#64748b", textAlign: "center", borderTop: "1px solid #334155", paddingTop: "15px" }}>
            Demo: <code>alice (tech123)</code> | <code>bob (hr123)</code> | <code>admin (admin123)</code>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", width: "100%", height: "100vh", background: "#0f172a" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 24px", background: "#1e293b", borderBottom: "1px solid #334155" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Shield size={24} color="#38bdf8" />
          <span style={{ fontWeight: "700", fontSize: "18px" }}>FinSolve Enterprise Assistant</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "#0f172a", padding: "6px 12px", borderRadius: "20px", border: "1px solid #334155", fontSize: "13px" }}>
            <span style={{ color: "#94a3b8" }}>User:</span>
            <strong>{userProfile.username}</strong>
            <span style={{ background: "#2563eb", padding: "2px 8px", borderRadius: "12px", fontSize: "11px", textTransform: "uppercase" }}>
              {userProfile.role}
            </span>
          </div>
          <button
            onClick={handleLogout}
            style={{ display: "flex", alignItems: "center", gap: "6px", background: "#334155", color: "#f8fafc", border: "none", padding: "7px 12px", borderRadius: "6px", cursor: "pointer", fontSize: "13px" }}
          >
            <LogOut size={14} /> Logout
          </button>
        </div>
      </header>

      <div style={{ flex: 1, overflowY: "auto", padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
        {messages.length === 0 && (
          <div style={{ textAlign: "center", margin: "auto", color: "#64748b" }}>
            <Shield size={48} style={{ opacity: 0.3, marginBottom: "12px" }} />
            <h3>Secure Enterprise Session Active</h3>
            <p style={{ fontSize: "14px", marginTop: "4px" }}>
              Authorized for: <strong>{userProfile.allowed_departments.join(", ").toUpperCase()}</strong> documents.
            </p>
          </div>
        )}

        {messages.map((msg, index) => (
          <div
            key={index}
            style={{
              alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
              maxWidth: "75%",
              background: msg.sender === "user" ? "#2563eb" : "#1e293b",
              border: msg.sender === "user" ? "none" : "1px solid #334155",
              borderRadius: "10px",
              padding: "14px 18px"
            }}
          >
            <p style={{ lineHeight: "1.5", fontSize: "14px", whiteSpace: "pre-wrap" }}>{msg.text}</p>

            {msg.sender === "bot" && (
              <div style={{ marginTop: "12px", paddingTop: "10px", borderTop: "1px solid #334155", fontSize: "11px", color: "#94a3b8" }}>
                {msg.latency && (
                  <div style={{ display: "flex", gap: "12px", marginBottom: "6px" }}>
                    <span>⏱️ Latency: {msg.latency}s</span>
                    {msg.tokens?.total_tokens > 0 && <span>🔢 Tokens: {msg.tokens.total_tokens}</span>}
                    <span>Status: <strong style={{ color: msg.status === "SUCCESS" ? "#4ade80" : "#f87171" }}>{msg.status}</strong></span>
                  </div>
                )}

                {msg.sources && msg.sources.length > 0 && (
                  <div style={{ marginTop: "6px" }}>
                    <div style={{ fontWeight: "600", marginBottom: "4px", color: "#cbd5e1" }}>Verified Sources:</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {msg.sources.map((src, i) => (
                        <span key={i} style={{ background: "#0f172a", border: "1px solid #475569", padding: "2px 8px", borderRadius: "4px" }}>
                          📄 {src.source} ({src.department}) • score: {src.rerank_score}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {chatLoading && (
          <div style={{ alignSelf: "flex-start", background: "#1e293b", padding: "12px 18px", borderRadius: "10px", color: "#94a3b8", fontSize: "13px" }}>
            Retrieving & Reranking from FinSolve Vector Store...
          </div>
        )}
      </div>

      <footer style={{ padding: "16px 24px", background: "#1e293b", borderTop: "1px solid #334155" }}>
        <form onSubmit={handleSend} style={{ display: "flex", gap: "10px" }}>
          <input
            type="text"
            placeholder="Ask about FinSolve policies, architecture, or tech specs..."
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            disabled={chatLoading}
            style={{ flex: 1, background: "#0f172a", border: "1px solid #475569", color: "#fff", padding: "12px 16px", borderRadius: "8px", outline: "none", fontSize: "14px" }}
          />
          <button
            type="submit"
            disabled={chatLoading || !inputQuery.trim()}
            style={{ background: "#2563eb", color: "#fff", border: "none", padding: "12px 20px", borderRadius: "8px", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px" }}
          >
            <Send size={16} /> Send
          </button>
        </form>
      </footer>
    </div>
  );
}