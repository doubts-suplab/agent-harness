# Publishing

How the HALO artifacts are published, and what external setup gates each channel. **Nothing publishes
automatically until the credentials/config below are in place** — the workflows fail closed.

Publishing is triggered by a **GitHub Release** (or manual `workflow_dispatch`). Bump the version first:
`bindings/python/pyproject.toml` and `bindings/java/pom.xml` must agree, and the release tag should match.

## Python → PyPI

- **Workflow:** [`.github/workflows/publish-python.yml`](../.github/workflows/publish-python.yml)
- **Method:** [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) — no API token is
  stored in the repo.
- **Gate (one-time):**
  1. Create the `agent-harness` project on PyPI.
  2. Add a **Trusted Publisher** for it: owner `doubts-suplab`, repo `agent-harness`, workflow
     `publish-python.yml`, environment `pypi`.
  3. Create a GitHub Environment named `pypi` (optionally with required reviewers).
- The build step (`python -m build`) runs regardless and validates the package is publishable; only the
  final publish step needs the gate.

## Java → Maven Central

- **Workflow:** [`.github/workflows/publish-maven-central.yml`](../.github/workflows/publish-maven-central.yml)
- **Method:** the `release` profile in [`bindings/java/pom.xml`](../bindings/java/pom.xml) — attaches
  sources + javadoc, GPG-signs, and deploys via the Central Publishing plugin. `autoPublish=false`, so the
  deployment is **staged** for a human to release in the [Central Portal](https://central.sonatype.com/).
- **Gate (one-time):**
  1. Register and **verify the namespace** (`com.agentharness`) on the Central Portal.
  2. Generate a Central **user token** and a **GPG key** (publish the public key to a keyserver).
  3. Add repo secrets: `CENTRAL_TOKEN_USERNAME`, `CENTRAL_TOKEN_PASSWORD`, `GPG_PRIVATE_KEY`,
     `GPG_PASSPHRASE`.
- A separate workflow, [`publish-java.yml`](../.github/workflows/publish-java.yml), already publishes the
  same artifact to **GitHub Packages** (a different channel, useful for the Aether consumers before Central
  is live).

> **Rebrand note.** If the proposed rename to `halo-agent-harness` /
> `com.suplab.agentharness:halo-agent-harness` (see [`roadmap.md`](roadmap.md)) happens, update the PyPI
> project name, the Trusted Publisher, the Maven `groupId`/`artifactId`, and the verified Central namespace
> accordingly.
