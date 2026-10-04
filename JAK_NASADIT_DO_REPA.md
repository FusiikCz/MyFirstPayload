# Jak nasadit tuto sanitizovanou sadu do repozitáře MyFirstPayload

Nic z toho není weaponizované. Vše je lab-only, token-protected a inertní
vůči internetu. Postup krok za krokem.

## 1. Co nahradit / přidat / smazat

| Akce | Soubor | Poznámka |
|------|--------|----------|
| **PŘIDAT** | `DISCLAIMER.md` | etické a právní hranice — povinné čtení |
| **PŘIDAT** | `DEFENSE.md` | jádro repo: obrana proti celému řetězu |
| **PŘIDAT** | `payload_lab.txt` | inertní keylogger (guard `lab.local`) |
| **PŘIDAT** | `worm_lab.txt` | inertní replikační demo (self-replikace OFF) |
| **PŘIDAT** | `lab/` | mock web + captcha (zranitelná i patchnutá varianta) |
| **NAHRADIT** | `c2.py` | token-protected, bind 127.0.0.1, rate-limit |
| **NAHRADIT** | `README.md` | přepsán na research + defense framing |
| **SMAZAT** | `payload.txt`, `worm.txt` | nahrazeny `*_lab.txt` (bez cílových cest) |
| **SMAZAT** | `revizePredNasazenim.md` | obsah přesunut do `DEFENSE.md` |
| **PONECHAT** | `main.py` | OCR pipeline; přidej k němu složku `samples/` |

## 2. Git příkazy (z klonu repa)

```bash
cd MyFirstPayload

# nahrazení a smazání starých souborů
git rm payload.txt worm.txt revizePredNasazenim.md
cp /cesta/k/repo_sanitized/c2.py            c2.py
cp /cesta/k/repo_sanitized/README.md        README.md
cp /cesta/k/repo_sanitized/DISCLAIMER.md    DISCLAIMER.md
cp /cesta/k/repo_sanitized/DEFENSE.md       DEFENSE.md
cp /cesta/k/repo_sanitized/payload_lab.txt  payload_lab.txt
cp /cesta/k/repo_sanitized/worm_lab.txt     worm_lab.txt
cp /cesta/k/repo_sanitized/JAK_NASADIT_DO_REPA.md .
mkdir -p lab && cp /cesta/k/repo_sanitized/lab/* lab/

git add -A
git commit -m "Sanitize to lab-only PoC: inert payloads, tokenized C2, defense docs, mock lab"
git push
```

## 3. Nastavení repozitáře na GitHubu

- **Description:** `Lab-only XSS/keylogger chain research PoC + defense (inert by design)`
- **Topics:** `security-research`, `xss`, `defense`, `lab-only`, `poc`
- **LICENSE:** přidej text s explicitním "no warranty / educational only"
  (obsah máš v DISCLAIMER.md; pro licenci použij MIT + odkaz na DISCLAIMER).
- **SECURITY.md** (volitelně): kam hlásit chyby dokumentace.

## 4. Jak pracovat dál (aby to šlo rozběhnout)

1. Lokální lab: `lab/README.md` (php -S, hosts, c2.py).
2. Pokusy veď na mocku — nikdy proti veřejnému webu.
3. Každý experiment zapisuj do sekce "Research notes" (README.md) nebo jako
   `notes/*.md`: co testuješ, jaká je úspěšnost, jaký má obrana dopad.
4. Užitečné metriky: úspěšnost OCR, počet replikací do zastavení rate-limitem,
   rozdíl událostí VULNERABLE vs PATCHED.
5. Rozšiřuj **obrannou** část (DEFENSE.md) — to je přidaná hodnota repo.

## 5. Zdůraznění disclaimeru (co je kde uděláno)

- README.md: blok `⚠️ DISCLAIMER` hned na začátku.
- DISCLAIMER.md: samostatný soubor s právními hranicemi (paragrafy + souhlas).
- DEFENSE.md: úvod "pokud jsi defender, začni tady".
- Každý payload/worm soubor: hlavička "LAB-ONLY, NEFUNGUJE veřejně".
- c2.py: název i logy obsahují `LAB-ONLY`.
- lab/: sekce "Co to NENÍ a nesmí být".
