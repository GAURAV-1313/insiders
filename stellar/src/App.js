import React, { useState, useEffect, useCallback, useMemo } from "react";
import { CONTRACT_ID, getIncidentCount, getIncident, explorerUrl } from "./stellar";
import IncidentCard from "./components/IncidentCard";
import StoreIncidentForm from "./components/StoreIncidentForm";
import "./App.css";

const DEMO_INCIDENTS = [];

// Theme colors — swap between dark and light
const themes = {
  dark: {
    bg: "bg-slate-950", text: "text-white", muted: "text-slate-400", faint: "text-slate-500", dimmer: "text-slate-600",
    card: "bg-slate-900 border-slate-800", cardHover: "hover:border-slate-700",
    input: "bg-slate-800 border-slate-700 text-white", header: "bg-slate-900/80 border-slate-800",
    hero: "from-slate-900 to-slate-950 border-slate-800", trustCard: "bg-slate-800/40 border-slate-700/40",
    pipeline: "bg-slate-800/60 border-slate-700/40", pipelineActive: "bg-indigo-900/60 border-indigo-500/40",
    tab: "bg-slate-900", tabActive: "bg-sky-600 text-white", tabInactive: "text-slate-400 hover:text-white hover:bg-slate-800",
    footer: "bg-slate-900/50 border-slate-800", badge: "bg-slate-800", scoreBg: "bg-slate-800/60 border-slate-700/40",
    toggle: "bg-slate-800 text-slate-400", divider: "border-slate-800", formula: "bg-slate-900/50",
  },
  light: {
    bg: "bg-gray-50", text: "text-gray-900", muted: "text-gray-500", faint: "text-gray-400", dimmer: "text-gray-400",
    card: "bg-white border-gray-200 shadow-sm", cardHover: "hover:border-gray-300",
    input: "bg-white border-gray-300 text-gray-900", header: "bg-white/90 border-gray-200",
    hero: "from-gray-100 to-gray-50 border-gray-200", trustCard: "bg-white border-gray-200 shadow-sm",
    pipeline: "bg-white border-gray-200 shadow-sm", pipelineActive: "bg-indigo-50 border-indigo-300",
    tab: "bg-gray-100", tabActive: "bg-sky-600 text-white", tabInactive: "text-gray-500 hover:text-gray-900 hover:bg-gray-200",
    footer: "bg-gray-100 border-gray-200", badge: "bg-gray-100", scoreBg: "bg-white border-gray-200 shadow-sm",
    toggle: "bg-gray-200 text-gray-600", divider: "border-gray-200", formula: "bg-gray-100",
  },
};

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
  const [expandedDates, setExpandedDates] = useState({});
  const [mode, setMode] = useState("dark");
  const t = themes[mode];

  const refreshCount = useCallback(() => {
    if (CONTRACT_ID && publicKey) {
      getIncidentCount().then(setCount).catch(console.error);
    }
  }, [publicKey]);

  // Fetch incidents from K8sWhisperer agent audit log (localhost:9000)
  const fetchFromAgent = useCallback(() => {
    fetch("http://localhost:9000/api/audit")
      .then((r) => r.json())
      .then((entries) => {
        if (!Array.isArray(entries)) return;
        const mapped = entries.map((e) => ({
          incident_id: e.incident_id || "unknown",
          anomaly_type: (e.anomaly || {}).type || "Unknown",
          severity: (e.anomaly || {}).severity || "MED",
          namespace: (e.anomaly || {}).namespace || "production",
          affected_resource: (e.anomaly || {}).affected_resource || "unknown",
          action: (e.plan || {}).action || "explain_only",
          timestamp: String(Math.floor(new Date(e.timestamp || 0).getTime() / 1000)),
          execution_status: e.execution_status || "",
          diagnosis: e.diagnosis || "",
          explanation: e.explanation || "",
          source: "agent",
        }));
        setIncidents((prev) => {
          const existingIds = new Set(prev.filter(i => i.source !== "agent").map(i => i.incident_id));
          const merged = prev.filter(i => i.source !== "agent");
          for (const inc of mapped) {
            if (!existingIds.has(inc.incident_id)) {
              merged.push(inc);
            }
          }
          return merged;
        });
      })
      .catch(() => {}); // agent may not be running
  }, []);

  useEffect(() => {
    refreshCount();
    fetchFromAgent();
    const countInterval = setInterval(refreshCount, 15000);
    const agentInterval = setInterval(fetchFromAgent, 10000);
    return () => { clearInterval(countInterval); clearInterval(agentInterval); };
  }, [refreshCount, fetchFromAgent]);

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

  // Group incidents by date, sorted newest-first
  const groupedByDate = useMemo(() => {
    const groups = {};
    for (const inc of incidents) {
      const ts = Number(inc.timestamp) * 1000;
      const dateKey = isNaN(ts) || ts === 0
        ? "Unknown Date"
        : new Date(ts).toLocaleDateString("en-US", { weekday: "short", year: "numeric", month: "short", day: "numeric" });
      const sortKey = isNaN(ts) || ts === 0 ? 0 : ts;
      if (!groups[dateKey]) groups[dateKey] = { items: [], sortKey };
      groups[dateKey].items.push(inc);
      if (sortKey > groups[dateKey].sortKey) groups[dateKey].sortKey = sortKey;
    }
    // Sort newest date first, within each date sort newest incident first
    return Object.entries(groups)
      .sort((a, b) => b[1].sortKey - a[1].sortKey)
      .map(([date, { items }]) => [
        date,
        items.sort((a, b) => Number(b.timestamp) - Number(a.timestamp)),
      ]);
  }, [incidents]);

  // Auto-expand the latest date
  useEffect(() => {
    if (groupedByDate.length > 0 && Object.keys(expandedDates).length === 0) {
      setExpandedDates({ [groupedByDate[0][0]]: true });
    }
  }, [groupedByDate]);

  // Agent performance metrics
  const totalIncidents = incidents.length;
  const resolved = incidents.filter(i => i.execution_status === "verified").length;
  const explained = incidents.filter(i => i.execution_status === "explained").length;
  const rejected = incidents.filter(i => i.execution_status === "rejected").length;
  const pending = incidents.filter(i => i.execution_status === "awaiting_approval").length;
  const avgConfidence = totalIncidents > 0
    ? (incidents.reduce((sum, i) => sum + (parseFloat(i.confidence) || 0.9), 0) / totalIncidents * 100).toFixed(0)
    : 0;
  // Agent effort score: resolved (full weight) + explained (partial — agent still diagnosed)
  const handled = resolved + explained;
  const agentScore = totalIncidents > 0 ? (((resolved * 1.0 + explained * 0.7) / totalIncidents) * 100).toFixed(0) : 0;
  const anomalyBreakdown = incidents.reduce((acc, inc) => {
    acc[inc.anomaly_type] = (acc[inc.anomaly_type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className={`min-h-screen ${t.bg} ${t.text} transition-colors duration-200`}>
      {/* Navigation */}
      <header className={`border-b ${t.header} backdrop-blur-sm sticky top-0 z-50`}>
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-sky-500 to-indigo-600 rounded-lg flex items-center justify-center font-bold text-sm shadow-lg shadow-sky-500/20">
              K8
            </div>
            <div>
              <h1 className={`font-bold text-lg leading-tight ${t.text}`}>K8sWhisperer</h1>
              <p className={`text-[11px] tracking-wide ${t.faint}`}>IMMUTABLE INCIDENT AUDIT ON STELLAR</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {CONTRACT_ID && (
              <a
                href={explorerUrl(CONTRACT_ID)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sky-500 text-sm hover:text-sky-400 transition-colors"
              >
                Block Explorer
              </a>
            )}
            <span className="bg-emerald-950 text-emerald-400 text-xs px-3 py-1 rounded-full border border-emerald-800">
              Testnet
            </span>
            <button
              onClick={() => setMode(m => m === "dark" ? "light" : "dark")}
              className={`${t.toggle} text-xs px-3 py-1.5 rounded-lg transition-colors`}
              title="Toggle theme"
            >
              {mode === "dark" ? "Light" : "Dark"}
            </button>
          </div>
        </div>
      </header>

      {/* Hero section */}
      <div className={`bg-gradient-to-b ${t.hero} border-b`}>
        <div className="max-w-7xl mx-auto px-6 py-10">
          <div className="flex gap-8 items-start">
            {/* Left: text + trust cards */}
            <div className="flex-1 min-w-0">
              <h2 className={`text-3xl font-bold ${t.text} mb-2`}>
                Tamper-Proof Kubernetes Incident Audit
              </h2>
              <p className={`${t.muted} text-lg max-w-xl mb-6`}>
                Every incident detected and remediated by the K8sWhisperer autonomous agent
                is permanently recorded on the Stellar blockchain. No one can alter the record
                after the fact -- not even the agent itself.
              </p>

              {/* Trust principles */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className={`${t.trustCard} border rounded-lg px-4 py-3`}>
                  <p className="text-sky-500 text-sm font-semibold mb-1">Transparent by Design</p>
                  <p className={`${t.faint} text-xs leading-relaxed`}>
                    The agent logs every decision it makes -- what it detected, why it acted, and what happened next. Nothing is hidden.
                  </p>
                </div>
                <div className={`${t.trustCard} border rounded-lg px-4 py-3`}>
                  <p className="text-emerald-500 text-sm font-semibold mb-1">Honest and Accountable</p>
                  <p className={`${t.faint} text-xs leading-relaxed`}>
                    On-chain records cannot be edited or deleted. If the agent made a mistake at 3am, the blockchain proves exactly what happened.
                  </p>
                </div>
                <div className={`${t.trustCard} border rounded-lg px-4 py-3`}>
                  <p className="text-violet-500 text-sm font-semibold mb-1">Trust but Verify</p>
                  <p className={`${t.faint} text-xs leading-relaxed`}>
                    Every incident card links to the Stellar block explorer. Engineers and auditors can independently verify the agent's actions.
                  </p>
                </div>
              </div>
            </div>

            {/* Right: Agent Performance Card */}
            <div className="w-64 flex-shrink-0 hidden lg:block">
              <div className={`${t.scoreBg} border rounded-xl p-5`}>
                <div className={`text-xs font-semibold ${t.muted} uppercase tracking-wider mb-4`}>Agent Scorecard</div>
                <div className="text-center mb-4">
                  <div className={`text-5xl font-bold ${
                    Number(agentScore) >= 80 ? "text-emerald-400" :
                    Number(agentScore) >= 50 ? "text-yellow-400" :
                    totalIncidents === 0 ? "text-slate-600" : "text-red-400"
                  }`}>
                    {totalIncidents > 0 ? `${agentScore}%` : "--"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">Agent Effectiveness</div>
                </div>
                <div className="space-y-2.5 text-xs">
                  <div className="flex justify-between"><span className={t.faint}>Total Handled</span><span className={`font-semibold ${t.text}`}>{handled}/{totalIncidents}</span></div>
                  <div className="flex justify-between"><span className={t.faint}>Auto-Resolved</span><span className="font-semibold text-emerald-400">{resolved}</span></div>
                  <div className="flex justify-between"><span className={t.faint}>Explained</span><span className="font-semibold text-sky-400">{explained}</span></div>
                  <div className="flex justify-between"><span className={t.faint}>Pending</span><span className="font-semibold text-yellow-400">{pending}</span></div>
                  <div className="flex justify-between"><span className={t.faint}>Rejected</span><span className="font-semibold text-red-400">{rejected}</span></div>
                  <div className="flex justify-between"><span className={t.faint}>On-Chain</span><span className="font-semibold text-indigo-400">{count !== null ? count : "--"}</span></div>
                  <div className="flex justify-between"><span className={t.faint}>Avg Confidence</span><span className="font-semibold text-violet-400">{totalIncidents > 0 ? `${avgConfidence}%` : "--"}</span></div>
                </div>
                <div className={`border-t ${t.divider} mt-4 pt-3`}>
                  <div className={`text-[10px] ${t.faint} mb-2`}>Score formula</div>
                  <div className={`text-[10px] ${t.dimmer} leading-relaxed font-mono ${t.formula} rounded px-2 py-1.5`}>
                    resolved x 1.0 + explained x 0.7
                  </div>
                  <div className={`text-[10px] ${t.dimmer} mt-1.5 leading-relaxed`}>
                    Explanations count — the agent still diagnosed the issue, fetched evidence, and surfaced it to the team.
                  </div>
                </div>
                <div className={`border-t ${t.divider} mt-3 pt-3 text-center`}>
                  <div className={`text-[10px] ${t.faint} leading-relaxed`}>
                    Acts when safe. Asks when uncertain. Every decision on-chain.
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Pipeline visualization */}
          <div className="flex items-center gap-1 overflow-x-auto pb-2">
            {PIPELINE_STAGES.map((stage, i) => (
              <React.Fragment key={stage.label}>
                <div className={`flex-shrink-0 px-3 py-2 rounded-lg text-center min-w-[90px] ${
                  i === 6
                    ? `${t.pipelineActive} border`
                    : `${t.pipeline} border`
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
          <div className={`${t.card} rounded-xl p-4 border`}>
            <p className={`${t.faint} text-xs uppercase tracking-wider`}>On-Chain</p>
            <p className={`text-3xl font-bold ${t.text} mt-1`}>
              {count !== null ? count : "--"}
            </p>
          </div>
          <div className={`${t.card} rounded-xl p-4 border`}>
            <p className={`${t.faint} text-xs uppercase tracking-wider`}>Local</p>
            <p className="text-3xl font-bold text-sky-400 mt-1">{incidents.length}</p>
          </div>
          <div className={`${t.card} rounded-xl p-4 border`}>
            <p className={`${t.faint} text-xs uppercase tracking-wider`}>Critical</p>
            <p className="text-3xl font-bold text-red-400 mt-1">{severityCounts.CRITICAL || 0}</p>
          </div>
          <div className={`${t.card} rounded-xl p-4 border`}>
            <p className={`${t.faint} text-xs uppercase tracking-wider`}>High</p>
            <p className="text-3xl font-bold text-orange-400 mt-1">{severityCounts.HIGH || 0}</p>
          </div>
          <div className={`${t.card} rounded-xl p-4 border`}>
            <p className={`${t.faint} text-xs uppercase tracking-wider`}>Contract</p>
            <p className="text-xs font-mono text-sky-400 mt-2 truncate">
              {CONTRACT_ID ? CONTRACT_ID.slice(0, 16) + "..." : "Not set"}
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className={`flex gap-1 mb-6 ${t.tab} rounded-lg p-1 w-fit`}>
          {[
            { key: "dashboard", label: "Incident Timeline" },
            { key: "store", label: "Store Incident" },
          ].map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-5 py-2 rounded-md text-sm font-medium transition-all ${
                tab === t.key
                  ? t.tabActive
                  : t.tabInactive
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "dashboard" && (
          <div className="flex gap-6">
            {/* Left: Incidents grouped by date */}
            <div className="flex-1 min-w-0">
              {/* Fetch bar */}
              <div className={`flex items-center gap-3 mb-6 ${t.card} rounded-xl p-3 border`}>
                <div className={`${t.muted} text-xs font-medium whitespace-nowrap`}>Fetch from chain:</div>
                <input
                  type="text"
                  placeholder="Public key (G...)"
                  value={publicKey}
                  onChange={(e) => setPublicKey(e.target.value)}
                  className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-mono text-white focus:border-sky-500 focus:outline-none transition-colors"
                />
                <input
                  type="text"
                  placeholder="Incident ID"
                  value={fetchId}
                  onChange={(e) => setFetchId(e.target.value)}
                  className="w-36 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-mono text-white focus:border-sky-500 focus:outline-none transition-colors"
                />
                <button
                  onClick={handleFetchIncident}
                  disabled={loading || !publicKey || !fetchId}
                  className="bg-sky-600 hover:bg-sky-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-xs px-4 py-1.5 rounded-lg font-medium transition-all"
                >
                  {loading ? "..." : "Fetch"}
                </button>
              </div>

              {/* Incidents grouped by date — collapsible, newest first */}
              {groupedByDate.length > 0 ? (
                groupedByDate.map(([date, dateIncidents]) => {
                  const isOpen = expandedDates[date] || false;
                  const sevCounts = dateIncidents.reduce((a, i) => { a[i.severity] = (a[i.severity] || 0) + 1; return a; }, {});
                  const types = [...new Set(dateIncidents.map(i => i.anomaly_type))];
                  return (
                    <div key={date} className="mb-3">
                      {/* Date header — clickable */}
                      <button
                        onClick={() => setExpandedDates(prev => ({ ...prev, [date]: !prev[date] }))}
                        className={`w-full ${t.card} ${t.cardHover} rounded-xl px-5 py-4 flex items-center gap-4 transition-all text-left group border`}
                      >
                        <div className={`${t.faint} transition-transform ${isOpen ? "rotate-90" : ""}`}>
                          <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor"><path d="M4 2l4 4-4 4"/></svg>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className={`text-sm font-semibold ${t.text}`}>{date}</div>
                          <div className={`text-xs ${t.faint} mt-0.5 truncate`}>
                            {types.join(", ")}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {sevCounts.CRITICAL > 0 && <span className="text-[10px] font-bold bg-red-950 text-red-400 px-2 py-0.5 rounded-full">{sevCounts.CRITICAL} CRIT</span>}
                          {sevCounts.HIGH > 0 && <span className="text-[10px] font-bold bg-orange-950 text-orange-400 px-2 py-0.5 rounded-full">{sevCounts.HIGH} HIGH</span>}
                          {sevCounts.MED > 0 && <span className="text-[10px] font-bold bg-yellow-950 text-yellow-400 px-2 py-0.5 rounded-full">{sevCounts.MED} MED</span>}
                          {sevCounts.LOW > 0 && <span className="text-[10px] font-bold bg-green-950 text-green-400 px-2 py-0.5 rounded-full">{sevCounts.LOW} LOW</span>}
                        </div>
                        <div className={`text-xs ${t.dimmer} tabular-nums w-20 text-right`}>
                          {dateIncidents.length} incident{dateIncidents.length !== 1 ? "s" : ""}
                        </div>
                      </button>
                      {/* Expanded cards */}
                      {isOpen && (
                        <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-3 ml-4 pl-4 border-l-2 ${t.divider}`}>
                          {dateIncidents.map((inc) => (
                            <IncidentCard key={inc.incident_id} incident={inc} txHash={null} mode={mode} />
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className={`text-center py-16 ${t.faint}`}>
                  <p className="text-lg">No incidents recorded yet</p>
                  <p className="text-sm mt-1">Start the K8sWhisperer agent to detect and remediate cluster anomalies</p>
                </div>
              )}
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

      {/* Footer */}
      <footer className={`border-t mt-16 ${t.footer}`}>
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <div className="w-6 h-6 bg-gradient-to-br from-sky-500 to-indigo-600 rounded flex items-center justify-center font-bold text-[10px]">
                  K8
                </div>
                <span className="font-semibold text-white">K8sWhisperer</span>
              </div>
              <p className={`${t.faint} text-sm max-w-md`}>
                An autonomous agent that acts when safe, asks when uncertain, and never
                hides what it did. Every action is on the blockchain -- transparent, honest,
                and permanently verifiable.
              </p>
            </div>
            <div className={`text-right text-sm ${t.faint}`}>
              <p>DevOps x AI/ML Track -- Hackathon 2026</p>
              <p className={`${t.dimmer} text-xs mt-1`}>
                LangGraph -- Groq -- Soroban -- React -- Tailwind
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
