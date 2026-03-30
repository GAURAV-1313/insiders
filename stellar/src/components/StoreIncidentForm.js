import React, { useState } from "react";
import { storeIncident } from "../stellar";

const ANOMALY_TYPES = [
  "CrashLoopBackOff",
  "OOMKilled",
  "Pending",
  "ImagePullBackOff",
  "Evicted",
  "CPUThrottling",
  "DeploymentStalled",
  "NodeNotReady",
];

const ACTIONS = [
  "restart_pod",
  "patch_memory_limit",
  "patch_cpu_limit",
  "delete_pod",
  "explain_only",
  "rollback_deployment",
  "log_node_metrics",
];

export default function StoreIncidentForm({ onStored }) {
  const [secretKey, setSecretKey] = useState("");
  const [form, setForm] = useState({
    incident_id: "",
    anomaly_type: "CrashLoopBackOff",
    severity: "HIGH",
    namespace: "production",
    affected_resource: "",
    action: "restart_pod",
    timestamp: Math.floor(Date.now() / 1000),
  });
  const [loading, setLoading] = useState(false);
  const [txHash, setTxHash] = useState("");
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setTxHash("");
    try {
      const hash = await storeIncident(secretKey, {
        ...form,
        timestamp: Number(form.timestamp),
      });
      setTxHash(hash);
      if (onStored) onStored(hash);
    } catch (err) {
      setError(err.message || "Transaction failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-900/40 to-sky-900/40 px-6 py-4 border-b border-slate-800">
          <h2 className="text-white font-semibold text-lg">Store Incident On-Chain</h2>
          <p className="text-slate-400 text-sm mt-1">
            Submit a K8sWhisperer incident record to the Stellar Soroban smart contract.
            This creates a permanent, tamper-proof audit entry.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Secret key */}
          <div>
            <label className="block text-slate-400 text-xs uppercase tracking-wider mb-1.5">
              Stellar Secret Key
            </label>
            <input
              type="password"
              placeholder="S..."
              value={secretKey}
              onChange={(e) => setSecretKey(e.target.value)}
              className="w-full bg-slate-800 text-white border border-slate-700 rounded-lg px-4 py-2.5 text-sm font-mono focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500/30 transition-all"
              required
            />
          </div>

          {/* Two-column grid */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-400 text-xs uppercase tracking-wider mb-1.5">
                Incident ID
              </label>
              <input
                name="incident_id"
                placeholder="e.g. inc-2026-001"
                value={form.incident_id}
                onChange={handleChange}
                className="w-full bg-slate-800 text-white border border-slate-700 rounded-lg px-3 py-2 text-sm focus:border-sky-500 focus:outline-none transition-all"
                required
              />
            </div>
            <div>
              <label className="block text-slate-400 text-xs uppercase tracking-wider mb-1.5">
                Affected Resource
              </label>
              <input
                name="affected_resource"
                placeholder="e.g. api-deploy-7c4f9"
                value={form.affected_resource}
                onChange={handleChange}
                className="w-full bg-slate-800 text-white border border-slate-700 rounded-lg px-3 py-2 text-sm focus:border-sky-500 focus:outline-none transition-all"
                required
              />
            </div>
            <div>
              <label className="block text-slate-400 text-xs uppercase tracking-wider mb-1.5">
                Anomaly Type
              </label>
              <select
                name="anomaly_type"
                value={form.anomaly_type}
                onChange={handleChange}
                className="w-full bg-slate-800 text-white border border-slate-700 rounded-lg px-3 py-2 text-sm focus:border-sky-500 focus:outline-none transition-all"
              >
                {ANOMALY_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-slate-400 text-xs uppercase tracking-wider mb-1.5">
                Severity
              </label>
              <select
                name="severity"
                value={form.severity}
                onChange={handleChange}
                className="w-full bg-slate-800 text-white border border-slate-700 rounded-lg px-3 py-2 text-sm focus:border-sky-500 focus:outline-none transition-all"
              >
                <option>CRITICAL</option>
                <option>HIGH</option>
                <option>MED</option>
                <option>LOW</option>
              </select>
            </div>
            <div>
              <label className="block text-slate-400 text-xs uppercase tracking-wider mb-1.5">
                Namespace
              </label>
              <input
                name="namespace"
                placeholder="production"
                value={form.namespace}
                onChange={handleChange}
                className="w-full bg-slate-800 text-white border border-slate-700 rounded-lg px-3 py-2 text-sm focus:border-sky-500 focus:outline-none transition-all"
              />
            </div>
            <div>
              <label className="block text-slate-400 text-xs uppercase tracking-wider mb-1.5">
                Remediation Action
              </label>
              <select
                name="action"
                value={form.action}
                onChange={handleChange}
                className="w-full bg-slate-800 text-white border border-slate-700 rounded-lg px-3 py-2 text-sm focus:border-sky-500 focus:outline-none transition-all"
              >
                {ACTIONS.map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 disabled:from-slate-700 disabled:to-slate-700 disabled:text-slate-500 text-white font-semibold py-3 rounded-lg transition-all shadow-lg shadow-sky-600/10 hover:shadow-sky-600/20"
          >
            {loading ? "Submitting to Stellar..." : "Store on Blockchain"}
          </button>
        </form>

        {/* Result */}
        {txHash && (
          <div className="mx-6 mb-6 bg-emerald-950/50 border border-emerald-800/50 rounded-lg p-4">
            <p className="text-emerald-400 text-sm font-medium mb-1">
              Incident stored on-chain successfully
            </p>
            <a
              href={`https://stellar.expert/explorer/testnet/tx/${txHash}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sky-400 text-xs font-mono hover:text-sky-300 underline break-all"
            >
              TX: {txHash}
            </a>
          </div>
        )}
        {error && (
          <div className="mx-6 mb-6 bg-red-950/50 border border-red-800/50 rounded-lg p-4">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}
      </div>

      {/* Info card */}
      <div className="mt-6 bg-slate-900/50 rounded-xl border border-slate-800 p-5">
        <h3 className="text-slate-300 font-medium text-sm mb-2">How it works</h3>
        <ol className="text-slate-500 text-sm space-y-1.5 list-decimal list-inside">
          <li>K8sWhisperer agent detects an anomaly in your Kubernetes cluster</li>
          <li>The agent diagnoses, plans, and executes a remediation (or escalates to human)</li>
          <li>Every decision is logged to <code className="text-sky-400 bg-slate-800 px-1.5 py-0.5 rounded text-xs">audit_log.json</code></li>
          <li>The incident is submitted to the Soroban smart contract on Stellar</li>
          <li>The record is permanent and verifiable via the block explorer</li>
        </ol>
      </div>
    </div>
  );
}
