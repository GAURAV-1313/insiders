"""K8sWhisperer runner — agent loop + webhook server, Windows compatible."""
import os
import sys
import threading
import json

sys.path.insert(0, "src")

os.environ.setdefault("K8SWHISPERER_USE_REAL_ADAPTERS", "true")
os.environ.setdefault("K8SWHISPERER_PUBLIC_BASE_URL", "https://keena-cryptogrammatical-christiana.ngrok-free.dev")

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

    def do_GET(self):
        if "/approve/" in self.path or "/reject/" in self.path:
            approved = "/approve/" in self.path
            incident_id = self.path.split("/")[-1]
            label = "Approved" if approved else "Rejected"
            accent = "#16a34a" if approved else "#dc2626"
            try:
                graph.invoke(
                    Command(resume={"approved": approved}),
                    config={"configurable": {"thread_id": incident_id}},
                )
                print(f"[webhook] incident {incident_id} {label.lower()}", flush=True)
                self._send(200, self._page(
                    f"{label}!",
                    f"Incident <code>{incident_id}</code> was {label.lower()}. "
                    "K8sWhisperer will resume execution now.",
                    accent
                ))
            except Exception as e:
                err = str(e)
                print(f"[webhook] resume error for {incident_id}: {err}", flush=True)
                # Checkpoint may have expired — still acknowledge the decision
                self._send(200, self._page(
                    f"Decision Recorded",
                    f"Your <b>{label.lower()}</b> decision for incident <code>{incident_id}</code> "
                    "was received. The agent has already completed this incident or it expired.",
                    "#f59e0b"
                ))
        else:
            self._send(404, "Not found")

    def do_POST(self):
        if self.path == "/webhook/slack":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            incident_id = body.get("incident_id")
            approved = bool(body.get("approved", False))
            try:
                graph.invoke(
                    Command(resume={"approved": approved}),
                    config={"configurable": {"thread_id": incident_id}},
                )
                self._send(200, '{"status":"ok"}', "application/json")
            except Exception as e:
                self._send(200, f'{{"status":"received","note":"{e}"}}', "application/json")


if __name__ == "__main__":
    agent_thread = threading.Thread(
        target=whisperer.run_forever,
        daemon=True,
        name="agent-loop"
    )
    agent_thread.start()

    server = ThreadingHTTPServer(("0.0.0.0", 9000), WebhookHandler)
    print("Webhook server running on http://0.0.0.0:9000", flush=True)
    print("ngrok url: https://keena-cryptogrammatical-christiana.ngrok-free.dev", flush=True)
    server.serve_forever()
