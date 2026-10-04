# MyFirstPayload — lab-only XSS/replication research PoC

> ## ⚠️ DISCLAIMER — READ BEFORE PROCEEDING
> This repository is **laboratory research material** intended for an
> isolated environment that you own. It is **not a tool for attacking real
> websites**. Executable code is deliberately inert outside the lab (host
> guard for `lab.local`, C2 at `127.0.0.1`, self-replication disabled by
> default). Attacking systems without authorization is illegal. See
> **[DISCLAIMER.md](DISCLAIMER.md)** for details.

## What this repository demonstrates

A complete **attack-chain case study** — and, above all, **how to defend
against it**:

```
[stored XSS in an ad]
        │  a visitor views the content → inline JS runs
        ▼
[payload] ──collects cookies / keystrokes / paste / forms──► [C2 server]
        │                                                    │
        └──beacon: waits for a command──────────────────────► │
                                                             ▼
                                              [SPREAD] replication loop:
                                              CAPTCHA OCR → new infected
                                              content → new infection → ...
```

**The repository's main value is `DEFENSE.md`** — concrete defenses for each
layer (CSP, output escaping, HttpOnly, rate limits, detection, and server
hardening).

## Contents

| File | Description |
|---|---|
| `DISCLAIMER.md` | Ethical and legal boundaries — read first |
| `DEFENSE.md` | **Core of the repository:** defenses for the full chain |
| `c2.py` | Collection/control server (LAB ONLY: binds to 127.0.0.1, token-protected) |
| `payload_lab.txt` | Inert keylogger demo (guarded to `lab.local`, C2 on localhost) |
| `worm_lab.txt` | Inert replication demo (self-replication disabled by default) |
| `index.php`, `captcha.php` | Mock website and CAPTCHA (vulnerable and patched modes) |
| `test_c2.sh`, `gen_captcha.py` | C2 smoke test and test CAPTCHA generator |

## Why the code is inert (and why it must stay that way)

| Safeguard | Effect |
|---|---|
| `if(location.host.indexOf("lab.local")<0)return` | The code will not run on another website; `lab.local` is not a public domain |
| `C = http://127.0.0.1:8080` | Data stays on the local machine |
| `P = base64("LABPAYLOADB64")` | The replication loop inserts a harmless placeholder unless deliberately changed in the lab |

**Do not remove these safeguards.** Understanding how an attack chain works
does not require a functional weapon; the chain is described and defenses
can be tested against the mock.

## Run the lab

```bash
# Dependencies: python3 -m pip install -r requirements.txt
#               PHP GD and Tesseract (e.g. sudo apt install php-gd tesseract-ocr)
# 1) hosts file: 127.0.0.1   lab.local
# 2) mock website: php -S 127.0.0.1:8000 -t . (from the repository root)
# 3) C2 server:    python3 c2.py (prints the TOKEN)
# 4) browser:      http://lab.local:8000       (VULNERABLE)
#                  http://lab.local:8000/?safe=1 (PATCHED — defense)
```

See `README.md` for details and test scenarios. Run the C2 self-test without
a browser:

```bash
bash test_c2.sh         # with Tesseract: PASS=10 FAIL=0 SKIP=0
```

## Research notes

- **CAPTCHA OCR:** Column segmentation and per-cell Tesseract voting across
  multiple configurations (height × PSM × inversion). Accuracy for the sum
  of the first two digits is approximately 70–85%; touching digits and
  italic "7" are common failure cases.
- **Replication without retries:** An OCR failure quietly ends the loop.
  Rate limiting on the server can further constrain automated submissions.
- **C2 without authentication is a liability:** The original design left
  `/export` open, exposing collected data to anyone. This sanitized version
  protects control endpoints with a token and binds only to localhost.

## Defense — TL;DR

1. **CSP without `unsafe-inline`** — blocks inline `onerror` handlers and
   exfiltration.
2. **`htmlspecialchars` on output** — prevents stored XSS.
3. **HttpOnly/Secure/SameSite cookies** — JavaScript cannot read the session
   cookie.
4. **Rate limits and a stronger CAPTCHA** — make automated submissions less
   effective.
5. **Detection** — CSP reports, outbound monitoring, and database audits for
   payload patterns.

See **`DEFENSE.md`** for implementation examples.

## License and use

See `DISCLAIMER.md`. Use this material only on systems you own or have
explicit written permission to test.
