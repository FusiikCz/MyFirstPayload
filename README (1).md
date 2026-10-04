# MyFirstPayload — lab-only XSS/replication research PoC

> ## ⚠️ DISCLAIMER — PŘEČTI SI PŘED ČIMKOLIV
> Tento repozitář je **laboratorní výzkumný materiál** pro vlastní izolované
> prostředí. **Není to nástroj k útoku na reálné weby.** Veškerý spustitelný
> kód je záměrně inertní vůči internetu (host-guard na `lab.local`, C2 na
> `127.0.0.1`, samo-replikace defaultně vypnutá). Zneužití proti cizím
> systémům je nelegální. Detaily: **[DISCLAIMER.md](DISCLAIMER.md)**.

## Co repo ukazuje

Kompletní **attack chain case study** — a především **jak se proti ní brát**:

```
[stored XSS v obsahu inzerátu]
        │  návštěvník zobrazí obsah → spustí se inline JS
        ▼
[payload] ──sběr: cookies / klávesy / paste / formuláře──► [C2 server]
        │                                                    │
        └──beacon: čeká na příkaz───────────────────────────► │
                                                             ▼
                                              [SPREAD] replikační smyčka:
                                              OCR captchy → nový infikovaný
                                              obsah → nová infekce → ...
```

**Hlavní hodnota repo: DEFENSE.md** — konkrétní obrana pro každou vrstvu
(CSP, output escaping, HttpOnly, rate-limity, detekce, server hardening).

## Struktura

| Soubor | Co je |
|---|---|
| `DISCLAIMER.md` | etické a právní hranice — povinné čtení |
| `DEFENSE.md` | **jádro repo**: obrana proti celému řetězu |
| `c2.py` | sběrný/řídicí server (LAB-ONLY: bind 127.0.0.1, token-protected) |
| `payload_lab.txt` | inertní keylogger demo (guard `lab.local`, C2 localhost) |
| `worm_lab.txt` | inertní replikační demo (self-replikace defaultně OFF) |
| `lab/` | mock web (zranitelná + zabezpečená varianta) + captcha + `test_c2.sh` |
| `captcha_ocr.py` | OCR pipeline pro captcha vzorky (segmentace + hlasování) |

## Proč je kód inertní (a proč to tak zůstane)

| Zábrana | Efekt |
|---|---|
| `if(location.host.indexOf("lab.local")<0)return` | na jakémkoli jiném webu se kód nespustí; `lab.local` neexistuje veřejně |
| `C = http://127.0.0.1:8080` | data zůstávají na lokálním stroji |
| `P = base64("LABPAYLOADB64")` | replikační smyčka vkládá neškodný placeholder, dokud ji výslovně nezapneš v labu |

**Neměň tyto zábrany.** K zodpovězení "jak by se to dalo zneužit" netřeba
funkční zbraň — attack chain je popsaný a obrana testovatelná na mocku.

## Jak spustit lab (5 minut)

```bash
# 1) hosts:  127.0.0.1   lab.local
# 2) mock web:   cd lab && php -S 0.0.0.0:8000      (php-gd potřebné)
# 3) C2:         python3 c2.py                      (vypíše TOKEN)
# 4) prohlížeč:  http://lab.local:8000              (VULNERABLE)
#                http://lab.local:8000/?safe=1      (PATCHED — obrana)
```

Detaily a testovací scénáře: `lab/README.md`.
Rychlý self-test C2 (token, sběr, beacon/spread, OCR) bez prohlížeče:

```bash
bash lab/test_c2.sh     # PASS=10 FAIL=0 = vše v pořádku
```

## Research notes

- **OCR captcha:** segmentace po sloupcích + per-cell tesseract s hlasováním
  přes konfigurace (výška × PSM × inverze). Úspěšnost ~70–85 % na součet
  prvních dvou číslic; slabinou jsou slepené číslice a kurzívní "7".
- **Replikace bez retry:** selhání OCR = tichý konec smyčky → reálný útočník
  by musel řešit retry; to je zároveň přirozený braking point, který lze
  na serveru zesílit rate-limitem.
- **C2 bez auth = self-own:** původní návrh nechával `/export` otevřený
  (kdokoli by stáhl ukradená data). Sanitizovaná verze tokenizuje
  vše řídící a binduje jen na localhost.

## Obrana — TL;DR

1. **CSP bez `unsafe-inline`** — zabije inline `onerror` i exfiltraci.
2. **`htmlspecialchars` na výstupu** — odstraní samotný stored XSS.
3. **HttpOnly/Secure/SameSite cookies** — session nelze ukrást JS.
4. **Rate-limit + oprava captchy** — ztíží replikaci k nepoužitelnosti.
5. **Detekce** — CSP reporty, outbound monitoring, DB audit na payload vzory.

Detailně s kódem: **DEFENSE.md**.

## Licence a užití

Viz DISCLAIMER.md. Používej výhradně na vlastních systémech nebo s písemným
oprávněním vlastníka.
