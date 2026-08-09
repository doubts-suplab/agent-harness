# Licensing — what AGPL-3.0 means if you build on HALO

HALO (`agent-harness`) is licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0). See
[`LICENSE`](LICENSE) for the full text. This page explains, in plain language, what that implies for people
who want to *use* HALO in their own software.

> **Not legal advice.** This is a good-faith summary to help you evaluate HALO, not a legal opinion. AGPL
> obligations depend on how you use the software and on your jurisdiction. If the answer matters to your
> business, talk to a lawyer.

## TL;DR

- **Use it, modify it, self-host it — freely.** AGPL grants broad rights.
- **The catch is distribution _and network use_.** AGPL-3.0 §13 extends copyleft to software offered *over
  a network*: if users interact with a covered work remotely, they must be able to get its **complete
  corresponding source** — including your modifications and, generally, the application combined with it.
- **This is the key difference from GPL/LGPL.** With AGPL there is no "SaaS loophole": running a modified
  version to provide a network service counts, even if you never ship a binary.

## What AGPL-3.0 requires

1. **Source availability.** Anyone who receives the software — or interacts with it over a network — can
   obtain the complete corresponding source under the same AGPL-3.0 terms.
2. **Same license (copyleft).** Derivative and combined works are licensed under AGPL-3.0.
3. **Notices preserved.** Keep copyright and license notices intact.
4. **State changes.** Mark modified files as changed.

## What this means for common scenarios

| You want to… | AGPL obligation |
|---|---|
| Evaluate, prototype, run HALO internally with **no external network users** | Use it freely; keep notices. Copyleft "conveying" isn't triggered by purely internal use. |
| Build a **SaaS / networked service** that imports HALO (even unmodified) and exposes it to users | The §13 network clause is very likely engaged: you must offer the **corresponding source of the combined work** to those users under AGPL-3.0. |
| **Modify** HALO and ship or host it | Your modifications are AGPL-3.0; publish their source. |
| Ship HALO **inside a proprietary product** you distribute | The combined/derivative work must be AGPL-3.0 — incompatible with keeping that product closed-source. |

Because HALO is imported as a library and its core is designed to sit *inside* your agent runtime, assume a
proprietary application that links HALO and serves it over a network forms a **combined work** subject to
AGPL-3.0. If your goal is to keep that application closed-source, AGPL-3.0 does not permit it.

## Your options if AGPL-3.0 doesn't fit

1. **Comply** — release the corresponding source of your combined/modified work under AGPL-3.0.
2. **Isolate** — keep HALO usage internal, with no external network users (evaluate the §13 boundary
   carefully; "internal" is narrower than it sounds once anyone outside your organisation interacts with it).
3. **Re-implement against the spec** — the [protocol](docs/spec/harness-protocol.md) is normative and
   language-neutral; a clean-room implementation of the *spec* is not a derivative of this *code*. (The spec
   text itself is part of this AGPL-3.0 repository; conforming implementations you write are your own work.)
4. **Ask about a commercial license** — HALO is **AGPL-3.0 only today**; no alternative/commercial license
   is offered at this time. If that changes it will be announced in [`CHANGELOG.md`](CHANGELOG.md).

## Why AGPL-3.0

HALO is a governance and oversight layer. AGPL keeps that layer — and improvements to it — open: anyone who
relies on a HALO-governed service can inspect the safety machinery deciding what agents are allowed to do.

## References

- Full text: [`LICENSE`](LICENSE) · <https://www.gnu.org/licenses/agpl-3.0.html>
- FSF FAQ on the AGPL and network use: <https://www.gnu.org/licenses/gpl-faq.html>
