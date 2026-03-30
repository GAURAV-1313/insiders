import React, { useState, useEffect, useCallback } from "react";
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

const PIPELINE_STAGES = [
  { label: "Observe", desc: "kubectl scan" },
  { label: "Detect", desc: "LLM classify" },
  { label: "Diagnose", desc: "Root cause" },
  { label: "Plan", desc: "Remediation" },
  { label: "Safety Gate", desc: "Risk routing" },
  { label: "Execute", desc: "kubectl action" },
  { label: "Audit", desc: "Stellar chain" },
];

export default function App() {
  const [incidents, setIncidents] = useState(DEMO_INCIDENTS);
  const [count, setCount] = useState(null);
  const [publicKey, setPublicKey] = useState(
    process.env.REACT_APP_PUBLIC_KEY || ""
  );
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("dashboard");
  const [fetchId, setFetchId] = useState("");

  const refreshCount = useCallback(() => {
    if (CONTRACT_ID && publicKey) {
      getIncidentCount().then(setCount).catch(console.error);
    }
  }, [publicKey]);

  useEffect(() => {
    refreshCount();
    const interval = setInterval(refreshCount, 15000);
    return () => clearInterval(interval);
  }, [refreshCount]);

  const handleFetchIncident = async () => {
    if (!publicKey || !fetchId) return;
    setLoading(true);
    try {
      const record = await getIncident(fetchId, publicKey);
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

  // Stats
  const severityCounts = incidents.reduce((acc, inc) => {
    acc[inc.severity] = (acc[inc.severity] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Navigation */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-sky-500 to-indigo-600 rounded-lg flex items-center justify-center font-bold text-sm shadow-lg shadow-sky-500/20">
              K8
            </div>
            <div>
              <h1 className="font-bold text-white text-lg leading-tight">K8sWhisperer</h1>
              <p className="text-slate-500 text-[11px] tracking-wide">IMMUTABLE INCIDENT AUDIT ON STELLAR</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {CONTRACT_ID && (
              <a
                href={explorerUrl(CONTRACT_ID)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sky-400 text-sm hover:text-sky-300 transition-colors"
              >
                Block Explorer
              </a>
            )}
            <span className="bg-emerald-950 text-emerald-400 text-xs px-3 py-1 rounded-full border border-emerald-800">
              Stellar Testnet
            </span>
          </div>
        </div>
      </header>

      {/* Hero section */}
      <div className="bg-gradient-to-b from-slate-900 to-slate-950 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-10">
          <h2 className="text-3xl font-bold text-white mb-2">
            Tamper-Proof Kubernetes Incident Audit
          </h2>
          <p className="text-slate-400 text-lg max-w-2xl mb-8">
            Every incident detected and remediated by the K8sWhisperer autonomous agent
            is permanently recorded on the Stellar blockchain. No one can alter the record
            after the fact -- not even the agent itself.
          </p>

          {/* Pipeline visualization */}
          <div className="flex items-center gap-1 overflow-x-auto pb-2">
            {PIPELINE_STAGES.map((stage, i) => (
              <React.Fragment key={stage.label}>
                <div className={`flex-shrink-0 px-3 py-2 rounded-lg text-center min-w-[90px] ${
                  i === 6
                    ? "bg-indigo-900/60 border border-indigo-500/40"
                    : "bg-slate-800/60 border border-slate-700/40"
                }`}>
                  <div className={`text-xs font-semibold ${i === 6 ? "text-indigo-300" : "text-slate-300"}`}>
                    {stage.label}
                  </div>
                  <div className="text-[10px] text-slate-500">{stage.desc}</div>
                </div>
                {i < PIPELINE_STAGES.length - 1 && (
                  <div className="text-slate-600 flex-shrink-0 text-xs">--</div>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
          <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
            <p className="text-slate-500 text-xs uppercase tracking-wider">On-Chain</p>
            <p className="text-3xl font-bold text-white mt-1">
              {count !== null ? count : "--"}
            </p>
          </div>
          <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
            <p className="text-slate-500 text-xs uppercase tracking-wider">Local</p>
            <p className="text-3xl font-bold text-sky-400 mt-1">{incidents.length}</p>
          </div>
          <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
            <p className="text-slate-500 text-xs uppercase tracking-wider">Critical</p>
            <p className="text-3xl font-bold text-red-400 mt-1">{severityCounts.CRITICAL || 0}</p>
          </div>
          <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
            <p className="text-slate-500 text-xs uppercase tracking-wider">High</p>
            <p className="text-3xl font-bold text-orange-400 mt-1">{severityCounts.HIGH || 0}</p>
          </div>
          <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
            <p className="text-slate-500 text-xs uppercase tracking-wider">Contract</p>
            <p className="text-xs font-mono text-sky-400 mt-2 truncate">
              {CONTRACT_ID ? CONTRACT_ID.slice(0, 16) + "..." : "Not set"}
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-slate-900 rounded-lg p-1 w-fit">
          {[
            { key: "dashboard", label: "Incident Timeline" },
            { key: "store", label: "Store Incident" },
          ].map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-5 py-2 rounded-md text-sm font-medium transition-all ${
                tab === t.key
                  ? "bg-sky-600 text-white shadow-lg shadow-sky-600/20"
                  : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "dashboard" && (
          <div>
            {/* Fetch bar */}
            <div className="flex items-center gap-3 mb-6 bg-slate-900 rounded-xl p-4 border border-slate-800">
              <div className="text-slate-400 text-sm font-medium whitespace-nowrap">Fetch from chain:</div>
              <input
                type="text"
                placeholder="Your public key (G...)"
                value={publicKey}
                onChange={(e) => setPublicKey(e.target.value)}
                className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono text-white focus:border-sky-500 focus:outline-none transition-colors"
              />
              <input
                type="text"
                placeholder="Incident ID"
                value={fetchId}
                onChange={(e) => setFetchId(e.target.value)}
                className="w-48 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono text-white focus:border-sky-500 focus:outline-none transition-colors"
              />
              <button
                onClick={handleFetchIncident}
                disabled={loading || !publicKey || !fetchId}
                className="bg-sky-600 hover:bg-sky-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm px-5 py-2 rounded-lg font-medium transition-all"
              >
                {loading ? "Loading..." : "Fetch"}
              </button>
            </div>

            {/* Incident grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {incidents.map((inc) => (
                <IncidentCard
                  key={inc.incident_id}
                  incident={inc}
                  txHash={null}
                />
              ))}
            </div>

            {incidents.length === 0 && (
              <div className="text-center py-16 text-slate-500">
                <p className="text-lg">No incidents recorded yet</p>
                <p className="text-sm mt-1">K8sWhisperer agent will submit incidents as they are detected and remediated</p>
              </div>
            )}
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

      {/* Footer */}
      <footer className="border-t border-slate-800 mt-16 bg-slate-900/50">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <div className="w-6 h-6 bg-gradient-to-br from-sky-500 to-indigo-600 rounded flex items-center justify-center font-bold text-[10px]">
                  K8
                </div>
                <span className="font-semibold text-white">K8sWhisperer</span>
              </div>
              <p className="text-slate-500 text-sm">
                Autonomous Kubernetes incident response agent with tamper-proof
                blockchain audit trail powered by Stellar Soroban.
              </p>
            </div>
            <div className="text-right text-sm text-slate-500">
              <p>DevOps x AI/ML Track -- Hackathon 2026</p>
              <p className="text-slate-600 text-xs mt-1">
                LangGraph -- Groq -- Soroban -- React -- Tailwind
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
