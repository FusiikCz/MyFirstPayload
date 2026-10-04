# DEFENSE — jak tento útok zastavit

Řetěz: **stored XSS → keylogger/krádež session → (volitelně) replikační smyčka
s OCR captchy**. Každá vrstva má konkrétní obranu. Nejúčinnější opatření jsou
na začátku.

## 1. Zlikvidovat spouštěč: CSP bez `unsafe-inline` (největší dopad)

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

- Bez `unsafe-inline` se **žádný inline handler** (`onerror=`) nespustí
  → payload se nespustí vůbec.
- `connect-src 'self'` + `img-src 'self'` zablokují i exfiltraci na C2
  (`new Image().src`, XHR na cizí doménu).
- Nasazuj postupně: nejdřív `Content-Security-Policy-Report-Only`, sbírej
  reporty, dolad, pak enforce.

## 2. Escapovat výstup (odstranit kořen: stored XSS)

Všechna uživatelská pole escapovat při renderu (PHP):

```php
echo htmlspecialchars($ad['text'], ENT_QUOTES | ENT_HTML5, 'UTF-8');
```

- Escapuj **při výstupu**, ne při uložení (data se mohou hodit i jinam).
- Doplňkově: validace na vstupu (délka, povolené tagy = žádné).
- Druhá vrstva: scrubbing uloženého obsahu (knihovna typu HTMLPurifier),
  pokud musí být HTML povoleno.

## 3. Session ochrana

```php
session_set_cookie_params([
  'lifetime' => 0, 'path' => '/', 'secure' => true,
  'httponly' => true, 'samesite' => 'Lax',
]);
```

- `HttpOnly` → `document.cookie` nevrátí PHPSESSID → krádež session padá.
- `SameSite` omezuje cross-site použítí.
- Rotace ID po přihlášení (`session_regenerate_id(true)`).

## 4. Captcha a rate-limity (proti automatizaci)

- Ta captcha je slabá: 4 číslice, odpověď = **součet prvních dvou**
  (pouhých 19 možností) + OCR čitelné ~70–85 %. Vylepšení:
  - nepoužívat aritmetiku z viditelných číslic; standardní decode úlohy,
  - zkreslení/šum, který neškodí čitelnosti pro lidi,
  - limit na nová API key (Google reCAPTCHA/Turnstile) pro citlivé akce.
- **Rate-limit** na vkládání: per-IP + per-session, např. max 3 inzeráty/hod.
- **Opravit Fatal error**: vstup `kod` validovat server-side (`ctype_digit`),
  vypnout `display_errors` (info leak cesty `/www/hosting/...`).

## 5. Detekce (co nastavit hned)

| Signál | Kde | Pravidlo |
|---|---|---|
| Inline script pokusy | CSP reporty | report-only → alarm na `/k?`, `/hello?co=` |
| Outbound na cizí IP | WAF/proxy log | `img-src`/XHR z prohlížečů na neznámé IP |
| Hromadné POSTy | access log | >N POSTů na vkládání z jedné session/IP |
| Payload v DB | DB audit | sken uložených textů na `onerror=`, `<script`, `javascript:` |
| Chybějící hlavičky | security scan | chybí CSP/X-Frame-Options/HttpOnly |

## 6. Server hardening

- Zavřít nepotřebné porty (FTP/POP3/IMAP); SFTP místo FTP.
- SSH: klíče, `PasswordAuthentication no`, fail2ban; ztracené heslo resetovat
  **přes konzoli poskytovatele**, ne brute-force.
- `display_errors=Off`, `log_errors=On`, oddělit error logy od webu.
- Zálohy DB a pravidelný audit uloženého obsahu.

## 7. Ověření obrany (test, který chceš udělat)

V labu (`lab/`) máš dvě varianty téže appky:
- `index.php` (VULNERABLE) — payload se spustí,
- `index.php?safe=1` (PATCHED: escaping + CSP) — payload se nespustí.

Vlož stejný payload do obou a porovnej: v PATCHED režimu se žádné události
na C2 neobjeví. To je měřitelný důkaz účinnosti obrany.
