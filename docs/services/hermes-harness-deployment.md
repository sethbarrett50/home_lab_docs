# Hermes Harness deployment readiness — HP and llm-01

**Status: planned; not installed on hp-lap. Last reviewed 2026-10-29.** This page is a deployment contract for `sethbarrett50/hermes-harness` (private GitHub repository), not a claim that native commands, code-editing workers, or host sandbox enforcement have been qualified.

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

## Pre-install blockers and linked issues

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

## Acceptance gate before deployment on HP

1. A tested Hermes-native skill or supported command routes the originating session into the existing Harness; `hermes-harness` CLI remains diagnostic, not the primary user surface.
2. A scoped, disposable worktree and operator-approved task produce a real local model proposal, independent review, functional verification, Git ownership audit and `pending_human_decision` with immutable receipts.
3. Worker and reviewer processes are proven to execute inside the intended OS security boundary. Git post-change audits and a broker socket alone are insufficient.
4. Model switching cannot stop protected gateway fallback or exceed the P4000 capacity; cancellation/UNKNOWN recovery cannot blindly replay potentially side-effecting jobs.
5. Approved credentials, Caddy/nftables rules, CT107 DNS and Mullvad guard remain unchanged by Harness installation. Test rollback; do not enable automatic pushes/merges.
6. Host-specific qualification, tests and remaining gaps are recorded in Harness `PROJECT_STATUS.md` and this runbook before considering the installation complete.

## Current rollback boundaries

No Harness-specific service or GPU switcher has yet been installed. Do not disable, stop or alter `llama-server.service`, `llama-qwen35-2b.service`, `hermes-gateway-7944f2ae.service`, Caddy, CT107 DNS, router policy routing or initramfs unlock as part of documentation or read-only qualification. Preserve existing encrypted-boot and Telegram access. Follow [Hermes gateway](hermes-gateway.md) and [Local LLM](local-llm.md) runbooks for service-specific recovery.
