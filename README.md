# MyFirstPayload — lab-only XSS/replication research PoC

> ## ⚠️ DISCLAIMER — READ BEFORE PROCEEDING
> This repository is **laboratory research material** intended for an
> isolated environment that you own. It is **not a tool for attacking real
> websites**. Executable code is deliberately inert outside the lab (host
> guard for `lab.local`, C2 at `127.0.0.1`, self-replication disabled by
> default). Attacking systems without authorization is illegal. See
> **[DISCLAIMER.md](DISCLAIMER.md)** for details.

# LAB — mock environment

An isolated mock website with vulnerable and patched modes for safely
studying the full chain. Nothing in this lab should be exposed to the public
internet.

## Quick start

Install the dependencies first:

```bash
# Python packages for the C2 server and CAPTCHA generator
python3 -m pip install -r requirements.txt

# System dependencies (Debian/Ubuntu)
sudo apt install php-cli php-gd tesseract-ocr
```

Then run these commands from the repository root:

```bash
# 1) Map the lab host (Linux/macOS: /etc/hosts; Windows: drivers\etc\hosts)
127.0.0.1   lab.local

# 2) Mock website — local access only (requires PHP GD)
php -S 127.0.0.1:8000 -t .

# 3) C2 server (in another terminal)
python3 c2.py          # prints the TOKEN

# 4) Open in a browser: http://lab.local:8000 (VULNERABLE) / ?safe=1 (PATCHED)
```

## Test scenario

1. **VULNERABLE mode:** Put the payload from `payload_lab.txt` in the "Text"
   field, submit it (enter the correct CAPTCHA sum), then open the created ad.
   The browser runs the JavaScript and events appear in the C2 dashboard.
2. **PATCHED mode:** Switch to `?safe=1` and submit the same payload. It is
   displayed as text and does not run (HTML escaping + CSP).
3. **Replication:** Use the payload from `worm_lab.txt`. After its beacon,
   run `curl "http://127.0.0.1:8080/spread?token=<TOKEN>"`. The worm solves
   the CAPTCHA through C2 `/solve` and submits new ads to the mock website.
4. **Measurement:** Use `/export?token=<TOKEN>` to get JSON for analysis
   (spread rate, OCR success rate, and rate-limit behavior).

## Automated self-test (no browser required)

`test_c2.sh` exercises the C2 chain on loopback and cleans up the server:

```bash
bash test_c2.sh
# Tests token protection (401/200), /hello /k /p /f (204),
# beacon -> spread -> beacon (SPREAD/consumed),
# /solve OCR against a Pillow-generated sample,
# and that /export contains events.
# With Pillow and Tesseract: PASS=10 FAIL=0 SKIP=0
# Without Tesseract: the OCR test is skipped.
```

`gen_captcha.py` generates a sample CAPTCHA in the style of `captcha.php`.
It writes the image to `/tmp/cap_lab.jpg` and the ground truth to
`/tmp/cap_lab.info`; the self-test uses it.

Note: `/solve` expects a base64-encoded image in the `?img=` query parameter.
URL-encode the base64 value (`curl -G --data-urlencode`) or `+` may be
interpreted as a space.

## Research notes

- OCR accuracy for the first two digits is approximately 70–85%. Measure how
  many replications fail; without retries, a failed payload stops quietly.
- CSP in PATCHED mode blocks `onerror` and XHR requests to C2 — this is the
  primary defense.
- The mock does not set HttpOnly cookies. `DEFENSE.md` describes how to
  configure them in a real application.
