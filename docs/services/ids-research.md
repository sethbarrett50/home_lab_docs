# IDS Research (Dissertation)

This homelab's IoT segment (VLAN 30) doubles as the real-world testbed for
Seth's dissertation research on drift-aware, uncertainty-quantified
intrusion detection. Documented here for reproducibility, per the repo's
[CONTRIBUTING.md](https://github.com/sethbarrett50/home_lab_docs/blob/main/CONTRIBUTING.md)
goal of being useful to anyone trying to reproduce or understand the setup.

## The research line

| Paper | Venue | Year | Summary |
|---|---|---|---|
| [FIRE: Fog-Based Intrusion Detection Framework for Real-Time Security in IoT Environments](https://doi.org/10.1007/978-3-032-07992-3_15) | Lecture Notes in Networks and Systems | 2025 | Earlier fog-based IDS framework for IoT — predecessor context for the FIRCE/FADES line. |
| [FLARE: Feature-Based Lightweight Aggregation for Robust Evaluation of IoT Intrusion Detection](https://doi.org/10.1007/978-3-032-23447-6_23) | LNICST | 2026 | Lightweight feature aggregation for evaluating IoT IDS performance. |
| [FIRCE: A Framework for Intrusion Response and Conformal Evaluation](https://doi.org/10.48550/arxiv.2605.01962) (preprint) / [published version](https://doi.org/10.1109/smartnets69662.2026.11604738) | arXiv preprint, published at IEEE SmartNets 2026 | 2026 | Augments supervised IDS classifiers with **conformal evaluation-based uncertainty quantification and drift detection**. Four conformal evaluation strategies (Inductive, Cross, Approximate Transductive, and a novel Approximate Cross-Conformal Evaluator), plus an adaptive chunking mechanism that adjusts evaluation granularity to stream volatility. Evaluated on **"a custom IoT testbed of 10 commercial devices"** plus CICIDS2018 and UNSW-NB15. |
| [FADES: Adaptive Drift Estimation via Conformal Signals for Streaming Intrusion Detection](https://doi.org/10.3390/electronics15102114) | *Electronics* (journal) | 2026 | Journal extension of FIRCE. Generalizes drift monitoring beyond prediction-space uncertainty to also support representation-space detectors (contrastive autoencoder / CADE) in a unified streaming architecture. Introduces Approx-CCE (statistical benefits of cross-conformal evaluation without repeated model training) and an Adaptive Chunking Controller. Evaluated across UNSW-NB15, CICIDS2018, **and a real-world IoT testbed**. |

## Likely connection to this network

Both FIRCE and FADES describe evaluation against a real/custom IoT testbed
— strongly likely to be this network's **VLAN 30** (192.168.30.0/24), which
currently hosts ~10 commercial IoT devices (Ring doorbell, Nest cam,
Google/Amazon smart speakers, Kasa smart plug, two robot vacuums, a baby
monitor, plus a couple still-unidentified devices — see
[devices/README.md](../devices/README.md)). **Needs confirmation from
owner** — this doc should be corrected if the actual research testbed is
separate hardware, not this home network.

## Unrelated device found during network migration

An unrecognized ESP32/8266 dev board (`ESP_512EA9`, `70:03:9F:51:2E:A9`) was
found on VLAN 30 during the September 2026 network migration. **Confirmed
by the owner to NOT be research equipment** — genuinely unknown origin, not
part of the FIRCE/FADES testbed. Currently firewall-blocked (MAC-based DROP
on the router, both input and forward-to-wan) but owner wants it fully
removed.

**Known gap:** the current block is router-level only. Since the board
shares the same VLAN 30 switch segment as the other IoT devices, it could
still communicate with them directly over L2 without ever traversing the
router's firewall — the block does not provide true isolation from other
devices on the same VLAN. Real fix is physical removal (once located) or
switch-level port isolation on the TL-SG108E, neither of which has been
done yet.

## TODO

- [ ] Confirm with owner whether VLAN 30 is in fact the testbed referenced
      in FIRCE/FADES, or if a different environment was used
- [ ] If confirmed, document actual data collection setup (packet capture
      method, attack simulation approach, labeling process)
- [ ] Locate and physically remove the unidentified ESP32 board, or apply
      switch-level port isolation if it can't be found
- [ ] Diagrams for the research data flow (tracked separately, issue #15)
