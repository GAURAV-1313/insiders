# K8sWhisperer Person 2 Scaffold

This repo implements the Person 2 orchestration layer for PS1:

- shared graph state
- LangGraph workflow wiring
- deterministic safety routing
- execution verification with backoff
- HITL pause/resume seams
- audit logging

The code is organized so Person 1 and Person 3 can plug in real adapters without changing the orchestration flow.

## Layout

- `src/k8swhisperer/state.py`: shared `TypedDict` contracts
- `src/k8swhisperer/runtime.py`: injected adapter/runtime configuration
- `src/k8swhisperer/bootstrap.py`: chooses fixture vs real adapters from env
- `src/k8swhisperer/graph.py`: graph builder and node routing
- `src/k8swhisperer/nodes/`: stage logic
- `src/k8swhisperer/adapters/`: integration protocols and fixture adapters
- `src/k8swhisperer/webhook.py`: FastAPI HITL resume seam
- `tests/`: routing and verification behavior tests

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Run Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Run One Development Cycle

```bash
cp .env.example .env
K8SWHISPERER_RUN_ONCE=true \
PYTHONPATH=src python3 main.py
```

`main.py` uses development fixture adapters while `K8SWHISPERER_USE_FIXTURES=true`.

## Run Continuous Polling Loop

```bash
cp .env.example .env
K8SWHISPERER_RUN_ONCE=false \
PYTHONPATH=src python3 main.py
```

## Teammate Handoff Files

- Person 1 should work in `src/k8swhisperer/adapters/kubectl_cluster.py`
- Person 3 should work in:
  - `src/k8swhisperer/adapters/openai_compatible_llm.py`
  - `src/k8swhisperer/adapters/slack_notifier.py`
  - `src/k8swhisperer/webhook.py`

## Switching To Real Integrations

Set the environment variables in `.env` and change:

```bash
K8SWHISPERER_USE_FIXTURES=false
```

Then `main.py` will build the real adapters instead of fixtures.
