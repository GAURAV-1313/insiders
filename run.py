"""K8sWhisperer runner — agent loop + webhook server, Windows compatible."""
import os
import sys
import threading
import json
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, "src")


from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

from k8swhisperer.app import create_app
from langgraph.types import Command

whisperer = create_app()
graph = whisperer.graph

DECISION_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
  <style>
    body {{ margin:0; min-height:100vh; display:grid; place-items:center;
           background:#0f172a; color:#e2e8f0;
           font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    .card {{ max-width:520px; margin:24px; padding:28px 32px; border-radius:16px;
             background:#111827; border:1px solid #1f2937;
             box-shadow:0 18px 40px rgba(0,0,0,.28); }}
    h1 {{ margin:0 0 12px; color:{accent}; font-size:28px; }}
    p {{ margin:0; line-height:1.6; color:#cbd5e1; }}
    code {{ background:#1f2937; padding:2px 6px; border-radius:6px; color:#f8fafc; }}
  </style>
</head>
<body><div class="card"><h1>{title}</h1><p>{body}</p></div></body>
</html>"""


class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[webhook] {format % args}", flush=True)

    def _send(self, code, body, content_type="text/html"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body.encode())

    def _page(self, title, body, accent):
        return DECISION_PAGE.format(title=title, body=body, accent=accent)

    def _extract_incident_id(self) -> str:
        parsed = urlparse(self.path)
        return parsed.path.rstrip("/").split("/")[-1]

    def _render_dashboard(self):
        from k8swhisperer.audit import load_audit_log
        entries = load_audit_log("audit_log.json")
        entries_reversed = list(reversed(entries))

        # Compute stats
        total = len(entries)
        auto_fixed = sum(1 for e in entries if e.get("execution_status") == "verified" and e.get("approved") is not True)
        hitl_approved = sum(1 for e in entries if e.get("approved") is True)
        hitl_rejected = sum(1 for e in entries if e.get("approved") is False)
        pending = sum(1 for e in entries if e.get("execution_status") == "awaiting_approval")
        explained = sum(1 for e in entries if e.get("execution_status") == "explained")

        # Build pending approval cards (shown at top with action buttons)
        pending_html = ""
        cards_html = ""

        for entry in entries_reversed:
            anomaly = entry.get("anomaly", {})
            plan = entry.get("plan", {})
            approved = entry.get("approved")
            result = entry.get("result", "")
            explanation = entry.get("explanation", "")
            exec_status = entry.get("execution_status", "")
            ts = (entry.get("timestamp", "")[:19] or "").replace("T", " ")
            iid = entry.get("incident_id", "")
            atype = anomaly.get("type", "unknown")
            severity = anomaly.get("severity", "?")
            pod = anomaly.get("affected_resource", "unknown")
            ns = anomaly.get("namespace", "")
            action = plan.get("action", "unknown")
            blast = plan.get("blast_radius", "?")
            confidence = plan.get("confidence", 0)
            diagnosis = entry.get("diagnosis", "")

            if exec_status == "verified":
                border = "#16a34a"; status_icon = "RESOLVED"; status_cls = "st-ok"
            elif approved is False or exec_status == "rejected":
                border = "#dc2626"; status_icon = "REJECTED"; status_cls = "st-reject"
            elif exec_status == "awaiting_approval":
                border = "#d97706"; status_icon = "AWAITING APPROVAL"; status_cls = "st-pending"
            elif exec_status == "explained":
                border = "#2563eb"; status_icon = "EXPLAINED"; status_cls = "st-info"
            elif exec_status == "verification_failed":
                border = "#dc2626"; status_icon = "VERIFY FAILED"; status_cls = "st-reject"
            else:
                border = "#2563eb"; status_icon = "PROCESSED"; status_cls = "st-info"

            approved_label = "Auto" if approved is None else ("Approved" if approved else "Rejected")
            safe_exp = explanation[:300].replace("<", "&lt;").replace(">", "&gt;")
            safe_pod = pod.replace("<", "&lt;")
            safe_diag = diagnosis[:200].replace("<", "&lt;").replace(">", "&gt;")

            # Approve/Reject buttons for pending incidents
            action_buttons = ""
            if exec_status == "awaiting_approval":
                action_buttons = f"""
              <div class="actions">
                <a class="btn btn-approve" href="/approve/{iid}">Approve</a>
                <a class="btn btn-reject" href="/reject/{iid}">Reject</a>
              </div>"""

            card = f"""
        <div class="card" style="border-left:4px solid {border}">
          <div class="card-header">
            <div class="meta">{ts} &middot; <code>{iid[:8]}...</code></div>
            <span class="status {status_cls}">{status_icon}</span>
          </div>
          <div class="title">{atype} <span class="badge sev-{severity.lower()}">{severity}</span></div>
          <div class="pod">Resource: <code>{ns}/{safe_pod}</code></div>
          <div class="row">
            <span>Action: <code>{action}</code></span>
            <span>Blast: <code>{blast}</code></span>
            <span>Confidence: <code>{confidence:.0%}</code></span>
            <span>Approval: <code>{approved_label}</code></span>
          </div>
          <div class="diagnosis"><strong>Diagnosis:</strong> {safe_diag}{'...' if len(diagnosis) > 200 else ''}</div>
          <div class="explanation"><strong>Summary:</strong> {safe_exp}{'...' if len(explanation) > 300 else ''}</div>{action_buttons}
        </div>"""

            if exec_status == "awaiting_approval":
                pending_html += card
            else:
                cards_html += card

        if not pending_html and not cards_html:
            cards_html = '<div class="empty">No incidents yet -- agent is monitoring the cluster.</div>'

        # Build pending section
        pending_section = ""
        if pending_html:
            pending_section = f"""
  <div class="section-header pending-header">ACTION REQUIRED -- {pending} incident(s) awaiting approval</div>
  {pending_html}
  <div class="divider"></div>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta http-equiv="refresh" content="5"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>K8sWhisperer Dashboard</title>
  <style>
    *{{box-sizing:border-box}}
    body{{margin:0;padding:24px 24px 80px;background:#0f172a;color:#e2e8f0;
         font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}}
    h1{{color:#38bdf8;margin:0 0 4px;font-size:28px;letter-spacing:-.5px;}}
    .subtitle{{color:#64748b;margin:0 0 16px;font-size:13px;}}

    /* Stats bar */
    .stats{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:24px;}}
    .stat{{background:#111827;border:1px solid #1f2937;border-radius:10px;
           padding:12px 18px;min-width:120px;text-align:center;}}
    .stat-value{{font-size:28px;font-weight:700;line-height:1;}}
    .stat-label{{font-size:11px;color:#64748b;margin-top:4px;text-transform:uppercase;letter-spacing:.5px;}}
    .sv-green .stat-value{{color:#4ade80;}}
    .sv-blue .stat-value{{color:#60a5fa;}}
    .sv-amber .stat-value{{color:#fbbf24;}}
    .sv-red .stat-value{{color:#f87171;}}
    .sv-cyan .stat-value{{color:#22d3ee;}}

    /* Section headers */
    .section-header{{font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:1px;
                     margin:24px 0 12px;padding:8px 12px;border-radius:6px;max-width:740px;}}
    .pending-header{{background:#78350f;color:#fbbf24;animation:pulse 2s ease-in-out infinite;}}
    @keyframes pulse{{0%,100%{{opacity:1;}} 50%{{opacity:.7;}}}}
    .divider{{border-top:1px solid #1e293b;margin:24px 0;max-width:740px;}}

    /* Cards */
    .card{{background:#111827;border:1px solid #1f2937;border-radius:12px;
           padding:16px 20px;margin-bottom:14px;max-width:740px;transition:border-color .2s;}}
    .card:hover{{border-color:#334155;}}
    .card-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;}}
    .meta{{color:#64748b;font-size:12px;}}
    .status{{font-size:10px;font-weight:700;padding:3px 10px;border-radius:99px;letter-spacing:.5px;}}
    .st-ok{{background:#14532d;color:#86efac;}}
    .st-reject{{background:#7f1d1d;color:#fca5a5;}}
    .st-pending{{background:#78350f;color:#fcd34d;animation:pulse 2s ease-in-out infinite;}}
    .st-info{{background:#1e3a5f;color:#93c5fd;}}
    .title{{font-size:18px;font-weight:600;color:#f1f5f9;margin-bottom:6px;}}
    .badge{{font-size:11px;padding:2px 8px;border-radius:99px;font-weight:700;vertical-align:middle;}}
    .sev-high{{background:#7f1d1d;color:#fca5a5;}}
    .sev-critical{{background:#5b0f0f;color:#ff8a8a;border:1px solid #dc2626;}}
    .sev-med{{background:#78350f;color:#fcd34d;}}
    .sev-low{{background:#14532d;color:#86efac;}}
    .pod{{color:#94a3b8;font-size:13px;margin-bottom:8px;}}
    .row{{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:#94a3b8;margin-bottom:8px;}}
    code{{background:#1f2937;padding:1px 6px;border-radius:4px;color:#f8fafc;font-size:12px;}}
    .diagnosis{{font-size:12px;color:#94a3b8;line-height:1.5;margin-bottom:6px;}}
    .explanation{{font-size:13px;color:#cbd5e1;line-height:1.55;
                  background:#0f172a;border-radius:6px;padding:10px;margin-top:8px;}}

    /* Action buttons */
    .actions{{display:flex;gap:10px;margin-top:12px;}}
    .btn{{display:inline-block;padding:8px 24px;border-radius:8px;font-size:14px;
         font-weight:600;text-decoration:none;cursor:pointer;transition:all .15s;}}
    .btn-approve{{background:#16a34a;color:#fff;}}
    .btn-approve:hover{{background:#15803d;transform:scale(1.03);}}
    .btn-reject{{background:#dc2626;color:#fff;}}
    .btn-reject:hover{{background:#b91c1c;transform:scale(1.03);}}

    .empty{{color:#475569;font-style:italic;padding:40px 0;text-align:center;font-size:15px;}}
    .footer{{position:fixed;bottom:0;left:0;right:0;background:#0f172a;border-top:1px solid #1e293b;
            padding:8px 24px;font-size:11px;color:#475569;}}
  </style>
</head>
<body>
  <h1>K8sWhisperer -- Live Incident Dashboard</h1>
  <p class="subtitle">Auto-refreshes every 5s &middot; Autonomous Kubernetes incident response agent</p>

  <div class="stats">
    <div class="stat sv-cyan"><div class="stat-value">{total}</div><div class="stat-label">Total Incidents</div></div>
    <div class="stat sv-green"><div class="stat-value">{auto_fixed}</div><div class="stat-label">Auto-Fixed</div></div>
    <div class="stat sv-blue"><div class="stat-value">{hitl_approved}</div><div class="stat-label">HITL Approved</div></div>
    <div class="stat sv-red"><div class="stat-value">{hitl_rejected}</div><div class="stat-label">Rejected</div></div>
    <div class="stat sv-amber"><div class="stat-value">{pending}</div><div class="stat-label">Pending</div></div>
    <div class="stat"><div class="stat-value">{explained}</div><div class="stat-label">Explained</div></div>
  </div>

  {pending_section}
  {cards_html}

  <div class="footer">K8sWhisperer &middot; DevOps x AI/ML &middot; LangGraph + kubectl + Groq + Stellar</div>
</body>
</html>"""

    def do_GET(self):
        if self.path in ("/dashboard", "/", ""):
            self._send(200, self._render_dashboard())
        elif "/approve/" in self.path or "/reject/" in self.path:
            approved = "/approve/" in self.path
            incident_id = self._extract_incident_id()
            if not incident_id:
                self._send(400, self._page("Bad Request", "Missing incident id in callback URL.", "#dc2626"))
                return
            label = "Approved" if approved else "Rejected"
            accent = "#16a34a" if approved else "#dc2626"
            print(
                f"[webhook] decision received: incident={incident_id} action={label.lower()} path={self.path}",
                flush=True,
            )
            # Send response immediately so browser doesn't time out
            self._send(200, self._page(
                f"{label}!",
                f"Incident <code>{incident_id}</code> was {label.lower()}. "
                "K8sWhisperer will resume execution now.",
                accent
            ))
            # Resume graph in background thread
            def _resume():
                config = {"configurable": {"thread_id": incident_id}}
                try:
                    if hasattr(graph, "get_state"):
                        try:
                            before = graph.get_state(config=config)
                            print(
                                f"[webhook] pre-resume state: incident={incident_id} next={getattr(before, 'next', None)}",
                                flush=True,
                            )
                        except Exception as e:
                            print(f"[webhook] pre-resume state read failed for {incident_id}: {e}", flush=True)
                    result = graph.invoke(
                        Command(resume={"approved": approved}),
                        config=config,
                    )
                    status = result.get("execution_status") if isinstance(result, dict) else "unknown"
                    print(
                        f"[webhook] incident {incident_id} {label.lower()} resume completed "
                        f"(execution_status={status})",
                        flush=True,
                    )
                    if hasattr(graph, "get_state"):
                        try:
                            after = graph.get_state(config=config)
                            print(
                                f"[webhook] post-resume state: incident={incident_id} next={getattr(after, 'next', None)}",
                                flush=True,
                            )
                        except Exception as e:
                            print(f"[webhook] post-resume state read failed for {incident_id}: {e}", flush=True)
                except Exception as e:
                    print(f"[webhook] resume error for {incident_id}: {e}", flush=True)
            threading.Thread(target=_resume, daemon=True).start()
        else:
            self._send(404, "Not found")

    def do_POST(self):
        if self.path == "/webhook/slack":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length)
                if not raw:
                    self._send(200, '{"status":"ok"}', "application/json")
                    return
                content_type = (self.headers.get("Content-Type") or "").lower()
                if "application/json" in content_type:
                    body = json.loads(raw)
                elif "application/x-www-form-urlencoded" in content_type:
                    form = parse_qs(raw.decode("utf-8", errors="ignore"))
                    payload_raw = form.get("payload", ["{}"])[0]
                    body = json.loads(payload_raw)
                else:
                    body = {}
                incident_id = body.get("incident_id")
                approved = str(body.get("approved", False)).strip().lower() in {"1", "true", "yes", "on"}
                print(
                    f"[webhook] POST callback received: incident={incident_id} approved={approved} content_type={content_type}",
                    flush=True,
                )
                if incident_id:
                    graph.invoke(
                        Command(resume={"approved": approved}),
                        config={"configurable": {"thread_id": incident_id}},
                    )
                self._send(200, '{"status":"ok"}', "application/json")
            except Exception:
                self._send(200, '{"status":"ok"}', "application/json")


if __name__ == "__main__":
    agent_thread = threading.Thread(
        target=whisperer.run_forever,
        daemon=True,
        name="agent-loop"
    )
    agent_thread.start()

    server = ThreadingHTTPServer(("0.0.0.0", 9000), WebhookHandler)
    print("Webhook server running on http://0.0.0.0:9000", flush=True)
    print(f"ngrok url: {os.environ.get('K8SWHISPERER_PUBLIC_BASE_URL', 'not set')}", flush=True)
    server.serve_forever()
