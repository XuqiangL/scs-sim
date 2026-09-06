# References — OSS inventory

Phase 1 cites these projects as **design references**. SCS-Sim is a clean-room
implementation (MIT). We do **not** vendor-copy large GPL codebases.

| Project | Role vs SCS-Sim | License (upstream) | Link |
|---------|-----------------|--------------------|------|
| **orbital-compute** | End-to-end “GPUs in orbit” stack: SGP4, power/thermal, ISL, scheduler. Informs Phase 3–4 ports. | MIT | https://github.com/ShipItAndPray/orbital-compute |
| **jaxsgp4** | JAX / GPU-batch SGP4. Optional accelerator after Phase 1; extra `jax` extra in `pyproject.toml` only. | check repo | search PyPI `jaxsgp4` / ESA & research ports |
| **Hypatia** | LEO network sim (ETH / IMC 2020): `satgenpy` + ns-3 + Cesium. Phase 2 routing / satviz inspiration. **ns3-sat-sim is GPL-2 — do not copy.** | MIT (satgenpy, satviz) / GPL-2 (ns-3) | https://github.com/snkas/hypatia |
| **StarPerf** | Mega-constellation performance + Cesium + scaling. Phase 2 area-to-area metrics inspiration. | check repo | https://github.com/SpaceNetLab/StarPerf_Simulator |
| **DSNS** | Event-driven LEO / interplanetary network (Oxford). Scalability + actor model for later clock/net. **GPLv3 — do not vendor.** | GPLv3 | https://github.com/ssloxford/DSNS · https://dsns.space |
| **LEOCraft** | Flow-level LEO (+Grid shells, throughput, stretch). Walker / shell config inspiration. | check repo | https://github.com/suvambasak/LEOCraft |
| **LEOPath** | Dynamic topology + pluggable routing + CesiumJS. Phase 2 routing-state harness. | check repo | https://github.com/Fundacio-i2CAT/LEOPath |
| **Orekit** | Java astrodynamics gold standard (force models, frames, events). Future high-fidelity adapter behind `PropagatorPort`. | Apache-2.0 | https://www.orekit.org/ |
| **poliastro** | Python astrodynamics (Astropy). Reference for Kepler/J2 formulas; project is in maintenance. | MIT | https://github.com/poliastro/poliastro |
| **humeris** | Python constellation / conjunction / analysis toolkit. Design reference for catalog ops. | check PyPI | https://pypi.org/project/humeris/ |
| **python-sgp4** | Brandon Rhodes SGP4 — **used in Phase 1** as an optional propagator. | MIT | https://github.com/brandon-rhodes/python-sgp4 |
| **CelesTrak** | TLE / OMM catalogs for real Starlink ephemerides (Phase 2+ ingestion, not Phase 1). | data TOS | https://celestrak.org/ |

## Standards / texts (formulas)

- Vallado, *Fundamentals of Astrodynamics and Applications* — J2 secular rates, GMST, PQW→IJK.
- Walker, J.G. — Walker-delta `i : T/P/F` geometry.
- WGS-84 / EGM96 — μ, Rₑ, J2 constants in `scs_sim/constants.py`.

## Policy

- Prefer **pure Python + numpy + sgp4** on Windows.
- Re-implement algorithms from textbooks and public papers.
- If an upstream file is GPL, read it only as a black-box behavior reference; do not paste.
