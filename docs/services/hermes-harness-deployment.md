# Hermes Harness deployment readiness — HP and llm-01

**Status: installed on hp-lap at pinned Harness `41fa1c3` (2026-10-29); limited local inference verified, live autonomous workflow NOT qualified.** This page is a deployment contract for `sethbarrett50/hermes-harness` (private GitHub repository), not a claim that native commands, code-editing workers, or host sandbox enforcement have been qualified.

## HP deployed Harness and XPS model pool — observed 2026-10-29

The dedicated `hermes` account deployed Hermes Harness (`sethbarrett50/hermes-harness`, private GitHub repository) in `/home/hermes/projects/hermes-harness-qualification` at **`41fa1c3bccfc6dd217f936c348f2a31bfc08f1c0`** (PRs #45–#46). The operator verified `uv sync --frozen --extra dev`, Harness import, six local enabled Hermes skills (`lets-investigate`, `what-we-know`, `game-plan`, `agents-assemble`, `cyber-warrior`, `stick-the-landing`), and active system gateway `hermes-gateway-7944f2ae.service`. The current dynamic bridge provides `xps-models` discovery and `xps-infer` for installed XPS Ollama models, plus approved worker/reviewer selection via `assemble-live --xps-worker-model NAME --xps-reviewer-model OTHER_NAME`. This is **not** proof that Hermes itself successfully completed an end-to-end task from Telegram. The six `SKILL.md` files are discoverable by Hermes but **do not register `/` commands with Telegram**; no phone slash-command autocomplete or gateway slash-command dispatch has been verified. Until a separate Telegram command/router integration is built, invoke these as ordinary-language requests to Hermes to use the named skill.

**XPS connection:** XPS systemd **user** unit `hermes-xps-tunnel.service` initiates a persistent SSH reverse tunnel to `pooltab@192.168.10.147`, exposing the XPS Ollama listener only on HP loopback `127.0.0.1:11435`. HP `curl http://127.0.0.1:11435/api/tags` saw twelve installed models, including Granite 4 3B, Qwen2.5-Coder 7B, Qwen3 8B and Cyber-Ornith 9B. HP's Harness dynamic `xps-infer --model granite4:3b` produced a real structured inference reply; fixed registry worker/reviewer tests also passed for Qwen2.5-Coder 7B and Qwen3 8B. No autonomous tool calls or host file changes are implied by these probes.

**Network scope:** The validated arrangement is **XPS → HP SSH reverse forwarding on the currently reachable lab route**, not HP → XPS inference over WireGuard. Do not claim WireGuard reachability, XPS listening public service, VPN failover or model API bearer authentication. HP loopback port 11435 can be used by other local HP users unless independently restricted. The SSH tunnel reconnects while the XPS systemd user manager runs; XPS sleep/offline or Wi-Fi isolation makes it unavailable. This connection does not require opening Ollama on the XPS LAN.

### Read-only operator checks — run on hp-lap

```bash
sudo systemctl is-active hermes-gateway-7944f2ae.service
sudo -u hermes -H bash -c '
  cd /home/hermes/projects/hermes-harness-qualification
  git log -1 --oneline
  uv run --frozen python -m hermes_harness.native.skill_bridge xps-models --session operator-check
  uv run --frozen python -m hermes_harness.native.skill_bridge doctor
  /home/hermes/.local/bin/hermes skills list
'
curl -fsS --max-time 5 http://127.0.0.1:11435/api/tags | jq -r '.models[].name'
```

On **XPS**, inspect `systemctl --user status hermes-xps-tunnel.service --no-pager` and `journalctl --user -u hermes-xps-tunnel.service -n 30 --no-pager`. The deployed `doctor` still does not assert fully qualified live execution or tool sandboxing. Do not restart the gateway, enable GPU switching, or automatically apply/push code as a diagnostic.

For exact operator approval boundaries and the disposable task workflow, see the Harness Harness repository file `docs/deployment/hp-lap.md` and Harness repository file `docs/user-guide/hermes-workflows.md`.

## Verified infrastructure

| Role | Host / service | Verified boundary |
|---|---|---|
| Coordinator | `hp-lap`, `hermes-gateway-7944f2ae.service` | Dedicated `hermes` UID 999; `/home/hermes` 0700; Codex primary, Telegram confirmed |
| Long-context fallback | `llm-01` :8081, `llama-qwen35-2b.service` | Qwen3.5 2B Q4_K_M, configured 65,536 tokens, `llm-long.home.arpa` authenticated HTTPS; local alias invoked |
| Short-context worker candidate | `llm-01` :8080, `llama-server.service` | Qwen3 8B Q4_K_M, configured 4,096 tokens, `llm.home.arpa` authenticated HTTPS; not a qualified 64K Hermes native agent |
| HTTPS / internal CA | Caddy CT106, `192.168.10.50` | Client allowlist Trusted VLAN + HP only; backend Caddy source restriction |
| DNS / privacy egress | CT107 `192.168.10.171` and Flint2 | HP DNS override and Mullvad exit observed; fail-closed and boot-order qualification pending |
| GPU | Proxmox VM108, Quadro P4000 8 GiB | Two active llama.cpp units consume ~7.2 GiB; no spare capacity assumed for third permanent model |

Actual local Qwen3.5 chat and terminal invocations worked, but repeated tool-call tests showed malformed schemas, tool search loops and inaccurate file-read claims. Do not route autonomous edits to it merely because the endpoint is healthy.

## Planned model residency policy — NOT DEPLOYED

**Preferred: hybrid.** Keep the Qwen3.5 2B 64K fallback service resident unless operator-approved maintenance explicitly takes it down. Allow a dedicated larger-model worker slot to rotate, replacing the currently resident Qwen3 8B with a qualified model (e.g. Granite candidate) only when hardware tests and scheduler support exist.

- Existing systemd units must be treated as externally owned until the Harness has an explicit authorized lifecycle policy. No auto-stopping or restarting them during preflight.
- Resource admission must account for observed weights, KV cache/context, concurrent requests, VRAM reserve and host RAM; one cross-process GPU lease, serial scheduling default.
- Switch lifecycle must drain, stop an authorized unit, start the next, validate identity/auth/readiness, record immutable evidence, and restore previous state on a safely recoverable error. UNKNOWN state fences retry.
- Do not interrupt a live fallback request, Codex primary or Telegram gateway to run background workers. The Hermes fallback chain is distinct from Harness per-role routing.
- Maintain per-role capability policies: tool-free analysis, bounded worker, independent reviewer and optional local-only security specialist. Model capability and OS-level confinement require independent evidence.

## Remaining production qualification and linked issues

- `hermes-harness#25` — llama.cpp/OpenAI-compatible endpoint qualification: auth, model identity, TLS, context, lifecycle and failure classification.
- `hermes-harness#24` — hybrid GPU model residency: pinned service policy, GPU lease, bounded transactional rotation and rollback.
- `hermes-harness#26` — Qwen/Granite evaluation: validated terminal receipts, tool schema success rates and correction/review quality.
- `hermes-harness#27` — HP integration qualification: native Hermes command invocation, bridge identity, approval/sandbox, deployment preflight and rollback.

Recent `hermes-harness/dev` incorporates bounded Ollama inference and immutable repair receipts using other models. This is reusable design evidence, **not** verification that the remote, authenticated llama.cpp endpoints or GPU switching are implemented. Do not duplicate the Harness's canonical broker/receipt/repair controller.

## Read-only preflight (no installs, no secrets)

```bash
# Run on hp-lap.
systemctl is-active hermes-gateway-7944f2ae.service
systemctl show hermes-gateway-7944f2ae.service -p User -p WorkingDirectory
sudo -u hermes -H /home/hermes/.local/bin/hermes fallback list
getent hosts llm.home.arpa llm-long.home.arpa
curl -sS -o /dev/null -w '%{http_code}\n' https://llm-long.home.arpa/v1/models
# Expected on an allowlisted client with CA installed, no bearer token: 401

# Run on llm-01.
systemctl is-active llama-server.service llama-qwen35-2b.service nftables.service
nvidia-smi
sudo ss -ltnp | grep -E ':8080|:8081'
sudo nft list ruleset
```

These checks alone **do not** establish reliability, security qualification or an authorized deployment. Model key material and OAuth credentials must never be printed in diagnostics. Any tests using keys should retrieve them from protected process environments/files rather than pass them as argv.

## Acceptance gate for production live execution on HP

1. A tested Hermes-native skill or supported command routes the originating session into the existing Harness; `hermes-harness` CLI remains diagnostic, not the primary user surface.
2. A scoped, disposable worktree and operator-approved task produce a real local model proposal, independent review, functional verification, Git ownership audit and `pending_human_decision` with immutable receipts.
3. Worker and reviewer processes are proven to execute inside the intended OS security boundary. Git post-change audits and a broker socket alone are insufficient.
4. Model switching cannot stop protected gateway fallback or exceed the P4000 capacity; cancellation/UNKNOWN recovery cannot blindly replay potentially side-effecting jobs.
5. Approved credentials, Caddy/nftables rules, CT107 DNS and Mullvad guard remain unchanged by Harness installation. Test rollback; do not enable automatic pushes/merges.
6. Host-specific qualification, tests and remaining gaps are recorded in Harness `PROJECT_STATUS.md` and this runbook before considering the installation complete.

## Current rollback boundaries

The Harness Python package and six native skill files are installed in the dedicated qualification checkout; **no separately qualified automatic GPU switcher or end-to-end worker executor is enabled**. Do not disable, stop or alter `llama-server.service`, `llama-qwen35-2b.service`, `hermes-gateway-7944f2ae.service`, Caddy, CT107 DNS, router policy routing or initramfs unlock as part of documentation or read-only qualification. Preserve existing encrypted-boot and Telegram access. Follow [Hermes gateway](hermes-gateway.md) and [Local LLM](local-llm.md) runbooks for service-specific recovery.
