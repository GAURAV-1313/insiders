import React, { useState, useEffect } from "react";
import { CONTRACT_ID, getIncidentCount, getIncident, explorerUrl } from "./stellar";
import IncidentCard from "./components/IncidentCard";
import StoreIncidentForm from "./components/StoreIncidentForm";
import "./App.css";

const DEMO_INCIDENTS = [
  {
    incident_id: "inc-demo-001",
    anomaly_type: "CrashLoopBackOff",
    severity: "HIGH",
    namespace: "production",
    affected_resource: "api-deployment-7d9f8b",
    action: "restart_pod",
    timestamp: "1704067200",
  },
  {
    incident_id: "inc-demo-002",
    anomaly_type: "OOMKilled",
    severity: "CRITICAL",
    namespace: "production",
    affected_resource: "ml-worker-5c8d9",
    action: "patch_memory_limit",
    timestamp: "1704153600",
  },
];

export default function App() {
  const [incidents, setIncidents] = useState(DEMO_INCIDENTS);
  const [count, setCount] = useState(null);
  const [publicKey, setPublicKey] = useState(
    process.env.REACT_APP_PUBLIC_KEY || ""
  );
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("dashboard");

  useEffect(() => {
    if (CONTRACT_ID && publicKey) {
      getIncidentCount().then(setCount).catch(console.error);
    }
  }, [publicKey]);

  const handleFetchIncident = async (id) => {
    if (!publicKey) return;
    setLoading(true);
    try {
      const record = await getIncident(id, publicKey);
      if (record) {
        setIncidents((prev) => {
          const existing = prev.find((i) => i.incident_id === record.incident_id);
          if (existing) return prev;
          return [record, ...prev];
        });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-800">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-sky-500 rounded-lg flex items-center justify-center font-bold text-sm">
              K8
            </div>
            <div>
              <h1 className="font-bold text-white">K8sWhisperer</h1>
              <p className="text-slate-400 text-xs">Stellar Audit Dashboard</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {CONTRACT_ID && (
              <a
                href={explorerUrl(CONTRACT_ID)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sky-400 text-sm hover:text-sky-300 underline"
              >
                View Contract ↗
              </a>
            )}
            <span className="bg-emerald-900 text-emerald-400 text-xs px-2 py-1 rounded-full">
              Testnet
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Stats bar */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <p className="text-slate-400 text-sm">On-Chain Incidents</p>
            <p className="text-3xl font-bold text-white mt-1">
              {count !== null ? count : "—"}
            </p>
          </div>
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <p className="text-slate-400 text-sm">Contract</p>
            <p className="text-sm font-mono text-sky-400 mt-1 truncate">
              {CONTRACT_ID ? CONTRACT_ID.slice(0, 20) + "…" : "Not configured"}
            </p>
          </div>
          <div className="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <p className="text-slate-400 text-sm">Network</p>
            <p className="text-lg font-semibold text-white mt-1">
              Stellar Testnet
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {["dashboard", "store"].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                tab === t
                  ? "bg-sky-600 text-white"
                  : "bg-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              {t === "dashboard" ? "Incident Dashboard" : "Store Incident"}
            </button>
          ))}
        </div>

        {tab === "dashboard" && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">
                Recorded Incidents
              </h2>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Public Key (G...) to fetch live"
                  value={publicKey}
                  onChange={(e) => setPublicKey(e.target.value)}
                  className="bg-slate-800 border border-slate-600 rounded px-3 py-1 text-sm font-mono text-white w-64"
                />
                <button
                  onClick={() => handleFetchIncident("inc-demo-001")}
                  disabled={loading || !publicKey}
                  className="bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-white text-sm px-3 py-1 rounded transition-colors"
                >
                  {loading ? "Loading…" : "Fetch"}
                </button>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {incidents.map((inc) => (
                <IncidentCard
                  key={inc.incident_id}
                  incident={inc}
                  txHash={null}
                />
              ))}
            </div>
          </div>
        )}

        {tab === "store" && (
          <StoreIncidentForm
            onStored={(hash) => {
              setTab("dashboard");
              if (count !== null) setCount(count + 1);
            }}
          />
        )}
      </main>

      <footer className="border-t border-slate-700 mt-12 py-6 text-center text-slate-500 text-sm">
        K8sWhisperer × Stellar — Immutable incident audit trail on the blockchain
      </footer>
    </div>
  );
}
