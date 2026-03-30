import React from "react";
import { txExplorerUrl } from "../stellar";

const SEVERITY_STYLES = {
  CRITICAL: { bg: "bg-red-950", border: "border-red-800", text: "text-red-400", badge: "bg-red-600" },
  HIGH: { bg: "bg-orange-950/50", border: "border-orange-800/50", text: "text-orange-400", badge: "bg-orange-500" },
  MED: { bg: "bg-yellow-950/30", border: "border-yellow-800/30", text: "text-yellow-400", badge: "bg-yellow-600" },
  LOW: { bg: "bg-green-950/30", border: "border-green-800/30", text: "text-green-400", badge: "bg-green-600" },
};

const ACTION_LABELS = {
  restart_pod: { label: "Restart Pod", color: "text-sky-400" },
  patch_memory_limit: { label: "Patch Memory (+50%)", color: "text-violet-400" },
  patch_cpu_limit: { label: "Patch CPU (+50%)", color: "text-violet-400" },
  delete_pod: { label: "Delete Pod", color: "text-orange-400" },
  explain_only: { label: "Explain Only", color: "text-slate-400" },
  rollback_deployment: { label: "Rollback Deploy", color: "text-red-400" },
  log_node_metrics: { label: "Log Node Metrics", color: "text-red-400" },
};

const ANOMALY_ICONS = {
  CrashLoopBackOff: "CL",
  OOMKilled: "OOM",
  Pending: "PND",
  ImagePullBackOff: "IMG",
  Evicted: "EVC",
  CPUThrottling: "CPU",
  DeploymentStalled: "STL",
  NodeNotReady: "NOD",
};

export default function IncidentCard({ incident, txHash }) {
  const sev = SEVERITY_STYLES[incident.severity] || SEVERITY_STYLES.MED;
  const actionInfo = ACTION_LABELS[incident.action] || { label: incident.action, color: "text-slate-400" };
  const icon = ANOMALY_ICONS[incident.anomaly_type] || "?";
  const ts = new Date(Number(incident.timestamp) * 1000);
  const timeStr = isNaN(ts.getTime()) ? "N/A" : ts.toLocaleString();

  return (
    <div className={`bg-slate-900 rounded-xl border ${sev.border} hover:border-sky-500/50 transition-all duration-200 overflow-hidden group`}>
      {/* Severity accent bar */}
      <div className={`h-1 ${sev.badge}`} />

      <div className="p-5">
        {/* Header row */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg ${sev.bg} border ${sev.border} flex items-center justify-center`}>
              <span className={`text-xs font-bold ${sev.text}`}>{icon}</span>
            </div>
            <div>
              <p className="text-white font-semibold text-sm leading-tight">
                {incident.anomaly_type}
              </p>
              <p className="text-slate-500 text-xs">{incident.namespace}</p>
            </div>
          </div>
          <span className={`${sev.badge} text-white text-[10px] font-bold px-2.5 py-1 rounded-full`}>
            {incident.severity}
          </span>
        </div>

        {/* Resource */}
        <div className="bg-slate-800/50 rounded-lg px-3 py-2 mb-3">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider">Affected Resource</p>
          <p className="text-white text-sm font-mono truncate">{incident.affected_resource}</p>
        </div>

        {/* Action + metadata */}
        <div className="flex items-center gap-2 mb-3">
          <span className={`text-xs font-medium ${actionInfo.color} bg-slate-800 px-2.5 py-1 rounded-md`}>
            {actionInfo.label}
          </span>
          <span className="text-xs text-slate-600">by K8sWhisperer agent</span>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-800">
          <div>
            <p className="text-slate-500 text-[11px]">{timeStr}</p>
            <p className="text-slate-600 text-[10px] font-mono truncate max-w-[180px]">
              {incident.incident_id}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {txHash && (
              <a
                href={txExplorerUrl(txHash)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sky-400 text-xs hover:text-sky-300 transition-colors bg-sky-950/50 px-2.5 py-1 rounded-md"
              >
                View TX
              </a>
            )}
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="On-chain" />
          </div>
        </div>
      </div>
    </div>
  );
}
