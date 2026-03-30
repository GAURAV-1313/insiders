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
        cards_html = ""
        for entry in entries_reversed:
            anomaly = entry.get("anomaly", {})
            plan = entry.get("plan", {})
            approved = entry.get("approved")
            result = entry.get("result", "")
            explanation = entry.get("explanation", "")
            ts = (entry.get("timestamp", "")[:19] or "").replace("T", " ")
            atype = anomaly.get("type", "unknown")
            severity = anomaly.get("severity", "?")
            pod = anomaly.get("affected_resource", "unknown")
            action = plan.get("action", "unknown")
            blast = plan.get("blast_radius", "?")
            if "verified" in result:
                border = "#16a34a"
            elif approved is False or "rejected" in result.lower():
                border = "#dc2626"
            elif "awaiting" in (result or "").lower():
                border = "#d97706"
            else:
                border = "#2563eb"
            approved_label = "Auto" if approved is None else ("Approved ✓" if approved else "Rejected ✗")
            safe_exp = explanation[:220].replace("<", "&lt;").replace(">", "&gt;")
            safe_pod = pod.replace("<", "&lt;")
            cards_html += f"""
        <div class="card" style="border-left:4px solid {border}">
          <div class="meta">{ts} &nbsp;·&nbsp; <code>{entry.get('incident_id','')[:8]}…</code></div>
          <div class="title">{atype} <span class="badge sev-{severity.lower()}">{severity}</span></div>
          <div class="pod">Pod: <code>{safe_pod}</code></div>
          <div class="row">
            <span>Action: <code>{action}</code></span>
            <span>Blast: <code>{blast}</code></span>
            <span>Human: <code>{approved_label}</code></span>
          </div>
          <div class="explanation">{safe_exp}{'…' if len(explanation) > 220 else ''}</div>
        </div>"""
        if not cards_html:
            cards_html = '<div class="empty">No incidents yet — agent is monitoring the cluster.</div>'
        count = len(entries)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta http-equiv="refresh" content="10"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>K8sWhisperer Dashboard</title>
  <style>
    *{{box-sizing:border-box}}
    body{{margin:0;padding:24px;background:#0f172a;color:#e2e8f0;
         font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}}
    h1{{color:#38bdf8;margin:0 0 4px;font-size:26px;}}
    .subtitle{{color:#64748b;margin:0 0 24px;font-size:13px;}}
    .card{{background:#111827;border:1px solid #1f2937;border-radius:12px;
           padding:16px 20px;margin-bottom:16px;max-width:740px;}}
    .meta{{color:#64748b;font-size:12px;margin-bottom:6px;}}
    .title{{font-size:18px;font-weight:600;color:#f1f5f9;margin-bottom:6px;}}
    .badge{{font-size:11px;padding:2px 8px;border-radius:99px;font-weight:700;}}
    .sev-high,.sev-critical{{background:#7f1d1d;color:#fca5a5;}}
    .sev-med{{background:#78350f;color:#fcd34d;}}
    .sev-low{{background:#14532d;color:#86efac;}}
    .pod{{color:#94a3b8;font-size:13px;margin-bottom:8px;}}
    .row{{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:#94a3b8;margin-bottom:10px;}}
    code{{background:#1f2937;padding:1px 6px;border-radius:4px;color:#f8fafc;font-size:12px;}}
    .explanation{{font-size:13px;color:#cbd5e1;line-height:1.55;
                  background:#0f172a;border-radius:6px;padding:10px;}}
    .empty{{color:#475569;font-style:italic;padding:40px 0;text-align:center;font-size:15px;}}
  </style>
</head>
<body>
  <h1>K8sWhisperer &mdash; Live Incident Dashboard</h1>
  <p class="subtitle">Auto-refreshes every 10&thinsp;s &nbsp;&middot;&nbsp; {count} incident(s) processed</p>
  {cards_html}
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
