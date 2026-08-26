# Host Bootstrap Expectations

- NEW project: resolve stable SHA, materialize the exact runtime, bootstrap, then create project state. Recovery is not required.
- RESUME project: use project state or verified Portable Recovery when state/artifacts were lost.
- SHA resolution on ChatGPT: GitHub Connector first, public GitHub Web/API second.
- Stable commits publish a commit-bound Runtime Release ZIP.
- Source/handoff ZIPs are not Recovery Bundles unless they carry a supported recovery manifest.
