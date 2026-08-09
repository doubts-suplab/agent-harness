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
  1. Create a PyPI account and the `halo-agent-harness` project (or let the first Trusted-Publishing
     upload create it).
  2. Add a **Trusted Publisher** for it: owner `doubts-suplab`, repo `agent-harness`, workflow
     `publish-python.yml`, environment `pypi`.
  3. Create a GitHub Environment named `pypi` (optionally with required reviewers).
- The build step (`python -m build`) runs regardless and validates the package is publishable; only the
  final publish step needs the gate.
- **Without any account**, users can still install from source:
  `pip install "git+https://github.com/doubts-suplab/agent-harness.git#subdirectory=bindings/python"`.

## Java → Maven Central

- **Workflow:** [`.github/workflows/publish-maven-central.yml`](../.github/workflows/publish-maven-central.yml)
- **Method:** the `release` profile in [`bindings/java/pom.xml`](../bindings/java/pom.xml) — attaches
  sources + javadoc, GPG-signs, and deploys via the Central Publishing plugin. `autoPublish=false`, so the
  deployment is **staged** for a human to release in the [Central Portal](https://central.sonatype.com/).
- **Gate (one-time):**
  1. Register on the Central Portal and **verify the namespace** `com.suplab.agentharness` — this requires
     proving control of a matching **domain** (`suplab.com`-style). If you do not own one, change the Maven
     `groupId` to **`io.github.doubts-suplab`**, which Central verifies via your GitHub account (no domain).
  2. Generate a Central **user token** and a **GPG key** (publish the public key to a keyserver).
  3. Add repo secrets: `CENTRAL_TOKEN_USERNAME`, `CENTRAL_TOKEN_PASSWORD`, `GPG_PRIVATE_KEY`,
     `GPG_PASSPHRASE`.
- A separate workflow, [`publish-java.yml`](../.github/workflows/publish-java.yml), already publishes the
  same artifact to **GitHub Packages** using the built-in `GITHUB_TOKEN` — **no external account**. This is
  the recommended channel until Central is set up; consumers resolve it with a `read:packages` token.
- **Without any account**, users can also clone the repo and `mvn install` the binding locally.

> **Do I need these accounts?** No — not to develop or to let others use HALO. You only need a PyPI and/or
> Sonatype Central account when you want the artifacts on the **public** registries. Until then, GitHub
> Packages (Java) and source installs (Python) cover distribution.
>
> **Coordinates (per [ADR-0013](decisions/ADR-0013-halo-rebrand.md)):** PyPI `halo-agent-harness`; Maven
> `com.suplab.agentharness:halo-agent-harness`.
