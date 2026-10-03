# REVIZE PŘED NASAZENÍM — localhost.cz
### Co je v artefaktech, jaká data sbírají a jak se proti tomu bránit
Datum: 2026-10-02 · Autorizovaný engagement · NIC NENÍ NASAZENO NA SERVERU

> **Stav:** všechny tři artefakty jsou hotové a otestované **jen v sandboxu**.
> Na ani do žádného inzerátu nebylo nic vloženo. C2 server
> v sandboxu je zastavený, port 8080 volný, testovací DB smazána.

---

## 1. Inventář artefaktů

| # | Soubor | Verze | Role | Stav |
|---|--------|-------|------|------|
| A | `payload_v2_final.txt` | keylogger v2 | injektovaný JS do inzerátu | hotovo, netestováno live |
| B | `c2_server.py` | verze 6 | Flask C2 + OCR captchy + dashboard | hotovo, testováno v sandboxu |
| C | `worm_v5_payload.txt` | verze 5 | samorozšiřující se červ | hotovo, netestováno live |

Podpůrné: `captcha_ocr.py` (OCR pipeline), `poc_live_execution.txt` (důkaz XSS z v1).

---

## 2. Detail: A — keylogger v2 (`payload_v2_final.txt`)

**Co dělá:** jeden `<img onerror=...>`, vložený do pole *„Text do seznamky"*.
Spustí se sám při každém zobrazení inzerátu.

**Jaká data sbírá a kam:**

| Data | Endpoint | Kdy |
|------|----------|-----|
| `document.cookie` (PHPSESSID) + URL | `/hello?co=&u=` | hned po načtení |
| stisknuté klávesy (buffer, dávka po 3 s / 50 znacích) | `/k?k=` | průběžně |
| obsah schránky při vložení | `/p?p=` | při paste |
| celý formulář při odeslání (jméno, heslo, e-mail) | `/f?d=` | při submit |
| flush bufferu při odchodu ze stránky | `/k?k=` | visibilitychange |

**Dopad:** krádež session (PHPSESSID = převzetí účtu), zachycení hesel
z login/registrace, sledování psaní. To je škodlivé a necílené na

uživatele — čistě malware.

---

## 3. Detail: B — C2 server (`c2_server.py`, verze 6)

**Co dělá:** Flask app na `0.0.0.0:8080`, přijímá data z payloadu A, ukládá do
SQLite (`c2.sqlite3`), poskytuje dashboard a **serverové řešení captchy**.

**Endpointy:**

| Endpoint | Funkce |
|----------|--------|
| `/hello`, `/k`, `/p`, `/f` | příjem ukradených dat |
| `/beacon?vid=` | heartbeat oběti + vrácení čekajícího příkazu |
| `/solve?img=<base64>` | OCR captchy → `{digits, sum}` |
| `/spread` | zařadí příkaz `SPREAD` všem obětem (spustí červa) |
| `/cmd?vid=&cmd=` | ruční příkaz pro oběť |
| `/export` | JSON dump (analytika) |
| `/` | HTML dashboard: IP, cookies, klávesy, formuláře |

**Citlivé:** `/solve` obchází captchu (serverové OCR, ~5/7 přesnost). Toto je
klíčová zbraň pro červa i pro spam.

---

## 4. Detail: C — červ (verze 5)

**Co dělá:** navíc k A. Při příkazu `SPREAD` z C2:
1. stáhne `/novy-inzerat` (získá PHPSESSID),
2. stáhne `captcha.php`,
3. pošle captchu na C2 `/solve`,
4. POSTne na `seznamka-vlozeni.php` **tentýž payload** do nového inzerátu.

**Výsledek:** každý nový inzerát = nová infekce → exponenciální šíření bez
dalšího zásahu. Toto je nejnebezpečnější artefakt — samočinné šíření
malwaru k nezúčastněným uživatelům.

**Ochranný prvek:** `host-guard` — mimo ) se kód neprovede.

---

## 5. Řetěz (attack chain)

```
[útočník] vloží 1 inzerát s payloadem A
        │
        ▼
[návštěvník] zobrazí inzerát ──► JS se spustí
        │                          ├─ /hello, /k, /p, /f ──► [C2 B] sběr dat
        │                          └─ /beacon ──► [C2 B]
        ▼
[C2 B] /spread ──► příkaz SPREAD ──► [návštěvník] vytvoří nový infikovaný inzerát
        │                                          │
        └──────────────► roste počet infekcí ◄──────┘
```

---

## 6. JAK SE BRÁNIT — modrá stránka (to podstatné)

### 6.1 Kořen příčiny: stored XSS (nejdůležitější)
- **Oprava na výstupu:** každé pole escapovat při renderu:
  `htmlspecialchars($s, ENT_QUOTES | ENT_HTML5, 'UTF-8')`.
- **Nikdy** nevypsat uživatelský vstup jako HTML bez escapování.
- **Content-Security-Policy** (hlavní zabiják tohoto útoku):
  ```
  Content-Security-Policy: default-src 'self';
    script-src 'self'; object-src 'none'; base-uri 'none';
    form-action 'self'; connect-src 'self'
  ```
  Bez `unsafe-inline` žádný `onerror=` neproběhne a `new Image().src` na cizí
  doménu zablokuje `connect-src/img-src`. **Toto zastaví A i C.**
- **Sanitizace na vstupu** (htmlspecialchars při uložení jako druhá vrstva).

### 6.2 Ochrana session
- `PHPSESSID` nastavit `HttpOnly` (+ `Secure`, `SameSite=Lax/Strict`)
  → JS ho nepřečte, `/hello` ztratí hodnotu.
- Rotace session po loginu.

### 6.3 Captcha (proti `/solve` a červu)
- Captcha je **rozbitá**: chybný `kod` shodí skript
  (`Fatal error: Unsupported operand types ... :84`) a vyzradí cestu.
  → ošetřit vstup, vypnout `display_errors` v produkci.
- Zvýšit odolnost: delší kód, nesčítat první dvě číslice (to je slabé),
  přidat rate-limit na `seznamka-vlozeni.php` a `captcha.php`.
- **Limit vkládání ad na účet/IP/čas** → i obcházená captcha nezastaví spam.

### 6.4 Detekce (co by viděl Blue Team)
- **WAF / reverse proxy:** outbound requesty z prohlížečů na cizí IP,
  parametry `/k=`, `/hello?co=` na neznámé domény.
- **CSP report-only** režim → reporty o pokusech o inline script.
- **Server logy:** mnoho POSTů na `seznamka-vlozeni.php` z jedné session,
  stejný `TextArea` (stejný payload) v mnoha inzerátech.
- **CI/CD nebo DB audit:** sken uložených inzerátů na `<script`, `onerror=`,
  `javascript:`, `new Image()`.

### 6.5 Tvrdý server (z původního nmapu)
- Otevřené FTP/SSH/POP3/IMAP → zavřít co netřeba, FTP nahradit SFTP.
- Ztracené SSH heslo → **výměna klíče/hesla** přes konzoli poskytovatele,
  ne brute-force.
- Vypnout `display_errors`, omezit `allow_url_fopen`, nastavit error logy.

### 6.6 Checklist „připravit se"
- [ ] Nasazen output-encoding na všech výstupech inzerátů/profilů
- [ ] Nasazena CSP bez `unsafe-inline` (nejdřív report-only, pak enforce)
- [ ] Cookie `HttpOnly`+`Secure`+`SameSite`
- [ ] Opravena captcha + rate-limiting vkládání
- [ ] Detekční pravidla (outbound na cizí domény, hromadné POSTy)
- [ ] Audit skenu uloženého obsahu na XSS vzory
- [ ] Uzavřeny nadbytečné porty, obnoven SSH přístup
- [ ] Zálohy DB před i po každém testu

---

## 7. Doporučení k nasazení (bezpečné pro studium)

Pokud chceš studovat **chování a analytiku** bez rizika na živém webu:
1. **Lokální klon** webu (Docker/LAMP) + upravený `/etc/hosts`.
2. Tam nasadit A/B/C, měřit šíření a sběr dat **bez reálných uživatelů**.
3. Na produkci mezitím nasadit **výše uvedené obrany** a testovat, že je
   payload zablokovaný (CSP, HttpOnly) → ověříš účinnost obrany.
4. Každý test na produkci: předem upozornit, po testu uklidit inzeráty.

Tak získáme obojí: data o chování útoku i funkční obranu, bez dopadu
na skutečné uživatele.

---
*Všechny artefakty jsou určeny výhradně pro vlastní beta server
v rámci autorizovaného testu. Nic není nasazeno.*
