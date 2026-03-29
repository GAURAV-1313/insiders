import React from "react";
import { txExplorerUrl } from "../stellar";

const SEVERITY_COLORS = {
  CRITICAL: "bg-red-600",
  HIGH: "bg-orange-500",
  MED: "bg-yellow-500",
  LOW: "bg-green-500",
};

const ACTION_LABELS = {
  restart_pod: "Restart Pod",
  patch_memory_limit: "Patch Memory",
  explain_only: "Explain Only",
};

export default function IncidentCard({ incident, txHash }) {
  const severityClass =
    SEVERITY_COLORS[incident.severity] || "bg-slate-500";

  return (
    <div className="bg-slate-800 rounded-xl p-5 border border-slate-700 hover:border-sky-500 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-xs text-slate-400 font-mono mb-1">
            {incident.incident_id}
          </p>
          <h3 className="text-white font-semibold text-lg">
            {incident.affected_resource}
          </h3>
          <p className="text-slate-400 text-sm">{incident.namespace}</p>
        </div>
        <span
          className={`${severityClass} text-white text-xs font-bold px-2 py-1 rounded-full`}
        >
          {incident.severity}
        </span>
      </div>

      <div className="flex gap-2 flex-wrap mb-4">
        <span className="bg-slate-700 text-sky-400 text-xs px-2 py-1 rounded font-mono">
          {incident.anomaly_type}
        </span>
        <span className="bg-slate-700 text-emerald-400 text-xs px-2 py-1 rounded">
          {ACTION_LABELS[incident.action] || incident.action}
        </span>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-slate-500 text-xs">
          {new Date(Number(incident.timestamp) * 1000).toLocaleString()}
        </p>
        {txHash && (
          <a
            href={txExplorerUrl(txHash)}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sky-400 text-xs hover:text-sky-300 underline"
          >
            View on Stellar ↗
          </a>
        )}
      </div>
    </div>
  );
}
