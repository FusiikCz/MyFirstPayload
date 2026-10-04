# DEFENSE — How to stop this attack

Chain: **stored XSS → keylogger/session theft → (optional) replication loop
using CAPTCHA OCR**. Each layer has a concrete defense. The most effective
measures are at the beginning of the chain.

## 1. Block execution: CSP without `unsafe-inline` (highest impact)

```
Content-Security-Policy: default-src 'self';
  script-src 'self';
  img-src 'self' data:;
  connect-src 'self';
  object-src 'none';
  base-uri 'none';
  form-action 'self';
  frame-ancestors 'self'
```

- Without `unsafe-inline`, inline handlers such as `onerror=` will not run,
  so the payload does not execute.
- `connect-src 'self'` and `img-src 'self'` block exfiltration to a third-
  party C2 through `new Image().src` or XHR.
- Roll out gradually: start with `Content-Security-Policy-Report-Only`,
  review reports, then switch to enforcement.

## 2. Escape output (remove the root cause: stored XSS)

Escape all user-provided fields when rendering them (PHP):

```php
echo htmlspecialchars($ad['text'], ENT_QUOTES | ENT_HTML5, 'UTF-8');
```

- Escape **on output**, not when storing data; the same data may be used
  elsewhere.
- Also validate input (length and allowed markup — preferably none).
- If HTML must be allowed, sanitize stored content with a library such as
  HTMLPurifier as an additional layer.

## 3. Protect sessions

```php
session_set_cookie_params([
  'lifetime' => 0, 'path' => '/', 'secure' => true,
  'httponly' => true, 'samesite' => 'Lax',
]);
```

- `HttpOnly` prevents `document.cookie` from returning the PHPSESSID, blocking
  this method of session theft.
- `SameSite` limits cross-site cookie use.
- Rotate the session ID after login with `session_regenerate_id(true)`.

## 4. CAPTCHA and rate limits (against automation)

- This CAPTCHA is weak: four digits, with the answer equal to the **sum of
  the first two** (only 19 possible results), and OCR readability of roughly
  70–85%. Improvements:
  - Do not derive the answer arithmetically from visible digits; use a
    standard challenge.
  - Add distortion/noise that does not impair human readability.
  - Consider Google reCAPTCHA or Turnstile for sensitive actions.
- **Rate-limit** submissions per IP and per session, e.g. at most three ads
  per hour.
- **Fix fatal errors:** validate the `kod` input server-side (for example
  with `ctype_digit`) and disable `display_errors` to prevent path disclosure
  such as `/www/hosting/...`.

## 5. Detection (what to configure now)

| Signal | Where | Rule |
|---|---|---|
| Inline script attempts | CSP reports | Start in report-only mode; alert on `/k?` and `/hello?co=` |
| Outbound requests to unknown IPs | WAF/proxy logs | Detect browser image/XHR requests to unknown IPs |
| Bulk POST requests | Access logs | Alert on more than N ad submissions from one session/IP |
| Payloads in the database | Database audit | Scan stored text for `onerror=`, `<script`, and `javascript:` |
| Missing headers | Security scan | Check for CSP, X-Frame-Options, and HttpOnly |

## 6. Server hardening

- Close unnecessary ports (FTP/POP3/IMAP); use SFTP instead of FTP.
- For SSH, use keys, set `PasswordAuthentication no`, and use fail2ban.
  Reset a lost password **through the provider console**, not by brute force.
- Set `display_errors=Off` and `log_errors=On`; keep error logs outside the
  web root.
- Back up the database and regularly audit stored content.

## 7. Verify the defense

The lab has two modes of the same app:
- `index.php` (VULNERABLE) — the payload runs.
- `index.php?safe=1` (PATCHED: escaping + CSP) — the payload does not run.

Submit the same test input in both modes and compare the results. In PATCHED
mode, no events should appear in C2. This is a measurable defense check.
