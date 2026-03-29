import React, { useState } from "react";
import { storeIncident } from "../stellar";

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
    <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
      <h2 className="text-white font-semibold text-lg mb-4">
        Store Incident On-Chain
      </h2>
      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          type="password"
          placeholder="Secret Key (S...)"
          value={secretKey}
          onChange={(e) => setSecretKey(e.target.value)}
          className="w-full bg-slate-900 text-white border border-slate-600 rounded px-3 py-2 text-sm font-mono"
          required
        />
        <div className="grid grid-cols-2 gap-3">
          <input
            name="incident_id"
            placeholder="Incident ID"
            value={form.incident_id}
            onChange={handleChange}
            className="bg-slate-900 text-white border border-slate-600 rounded px-3 py-2 text-sm"
            required
          />
          <input
            name="affected_resource"
            placeholder="Pod Name"
            value={form.affected_resource}
            onChange={handleChange}
            className="bg-slate-900 text-white border border-slate-600 rounded px-3 py-2 text-sm"
            required
          />
          <select
            name="anomaly_type"
            value={form.anomaly_type}
            onChange={handleChange}
            className="bg-slate-900 text-white border border-slate-600 rounded px-3 py-2 text-sm"
          >
            <option>CrashLoopBackOff</option>
            <option>OOMKilled</option>
            <option>Pending</option>
          </select>
          <select
            name="severity"
            value={form.severity}
            onChange={handleChange}
            className="bg-slate-900 text-white border border-slate-600 rounded px-3 py-2 text-sm"
          >
            <option>CRITICAL</option>
            <option>HIGH</option>
            <option>MED</option>
            <option>LOW</option>
          </select>
          <input
            name="namespace"
            placeholder="Namespace"
            value={form.namespace}
            onChange={handleChange}
            className="bg-slate-900 text-white border border-slate-600 rounded px-3 py-2 text-sm"
          />
          <select
            name="action"
            value={form.action}
            onChange={handleChange}
            className="bg-slate-900 text-white border border-slate-600 rounded px-3 py-2 text-sm"
          >
            <option value="restart_pod">restart_pod</option>
            <option value="patch_memory_limit">patch_memory_limit</option>
            <option value="explain_only">explain_only</option>
          </select>
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-sky-600 hover:bg-sky-500 disabled:bg-slate-600 text-white font-semibold py-2 rounded transition-colors"
        >
          {loading ? "Submitting to Stellar…" : "Store on Blockchain"}
        </button>
      </form>
      {txHash && (
        <p className="mt-3 text-emerald-400 text-sm break-all">
          ✓ Stored! TX:{" "}
          <a
            href={`https://stellar.expert/explorer/testnet/tx/${txHash}`}
            target="_blank"
            rel="noopener noreferrer"
            className="underline"
          >
            {txHash.slice(0, 16)}…
          </a>
        </p>
      )}
      {error && <p className="mt-3 text-red-400 text-sm">{error}</p>}
    </div>
  );
}
