# DISCLAIMER / ETHICAL AND LEGAL BOUNDARIES

**This repository is laboratory research material only.**

## What this is

An educational proof of concept demonstrating a *stored XSS → keylogger →
replication loop* chain and, above all, **how to defend against it**
(`DEFENSE.md`).

## What this is not — and must not become

- **It is not a tool to deploy against any real website.**
- All test code is deliberately inert outside the lab:
  - The host guard allows execution only on `lab.local`, a non-public domain
    mapped locally in `/etc/hosts`.
  - The C2 address is `127.0.0.1`.
  - Self-replication is disabled by default (placeholder).
- **Removing these safeguards and using the code against systems without
  permission is illegal.** Laws vary by jurisdiction; obtain authorization
  before testing.

## Consent and responsibility

- Use this only on systems **you own** or for which you have the owner's
  **written authorization** (for example, an in-scope bug bounty or contract).
- The repository author is not responsible for third-party misuse. Downloading
  or cloning this repository does not grant permission to test someone else's
  systems.
- This material is published for research and defense: to understand an
  attack so it can be stopped.

## If you are a defender

You are in the right place: this repository examines the chain as a defensive
case study. Start with **`DEFENSE.md`** for CSP, output escaping, HttpOnly,
rate limits, and detection.
