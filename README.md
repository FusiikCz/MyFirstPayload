# Repo overview

Tento repozitář obsahuje jednoduchý proof-of-concept stack pro:
- OCR CAPTCHA v Pythonu,
- server pro sběr dat z prohlížeče,
- JavaScript payload, který odesílá data na C2 server,
- ukázku jednoduchého „worm-like“ šíření v omezeném testovacím prostředí.

Vše je navrženo jako lokální demonstrační materiál, ne jako produkční aplikace ani nasazený webový systém.

---

## Struktura repozitáře

### main.py
Hlavní skript pro OCR captcha. Rozpoznává obrázek s 4 sloupci čísel na zeleném pozadí, rozdělí ho na segmenty, aplikuje různé OCR konfigurace přes Tesseract a vrátí řetězec čísel.

V praxi:
- načte obrázek z disku,
- vytvoří binární masku bílých pixelů,
- spočítá bílé pixely po sloupcích,
- rozsekne obraz na 4 části,
- použije Tesseract pro každý segment,
- vrátí čísla a součet prvních dvou.

### c2.py
Flask server pro příjem dat z prohlížeče a pro zpracování captcha. Ukládá data do SQLite databáze a poskytuje jednoduché endpointy pro:
- `/hello` – příchod nové oběti / cookies / URL,
- `/k` – keylogging data,
- `/p` – obsah schránky,
- `/f` – data formuláře,
- `/beacon` – heartbeat / příkazy pro oběť,
- `/solve` – OCR captcha z base64 obrázku.

Součástí je i jednoduchý dashboard a logování událostí do databáze.

### payload
Ukázkový JavaScript payload, který má být vložen do prohlížeče. Zachytává:
- cookies,
- text psaný na klávesnici,
- data formulářů při submitu,
- aktuální URL a další metadata,
- a odesílá je na C2 endpoint.

Tento soubor je spíše reference pro testování chování v izolovaném prostředí.

### worm
Ukázka „šířícího se“ payloadu, která simuluje známé schéma v omezeném sandboxovém prostředí:
- získá nový inzerát / formulář,
- stáhne captcha,
- odešle ji na C2 `/solve`,
- spočítá výsledek,
- repopuluje payload / další přístup.

To je demonstrační workflow pro studium automatického šíření v kontrolovaném prostředí.

---

## Jak spolu soubory pracují

1. `payload` běží v prohlížeči.
2. Odesílá data na `c2.py` přes HTTP endpointy.
3. `c2.py` ukládá data do SQLite a zpracovává captcha přes OCR.
4. `main.py` obsahuje podobnou logiku OCR jako serverová část, ale běží lokálně nad obrázkem na disku.
5. `worm` slouží jako ukázka automatizace a replikace v omezeném experimentálním prostředí.

---

## Předpoklady

Python balíčky:
- Flask
- Pillow
- NumPy
- Tesseract OCR nainstalovaný v systému

Pro lokální běh:

```bash
pip install flask pillow numpy
python c2.py
```

A potom:

```bash
python main.py capx.png
```

---

## Důležité upozornění

Tento repozitář je určen výhradně pro:
- bezpečnostní výzkum,
- interní demo a lokální testování,
- autorizované experimenty v izolovaném prostředí.

Není určen k produkčnímu nasazení ani k použití proti reálným službám, uživatelům nebo webům bez výslovného oprávnění.

---

## Shrnutí

Repo je v podstatě malý demonstrační projekt, který kombinuje:
- OCR pro segmentované captcha,
- Python Flask server pro sběr dat,
- JS payload pro záznam kláves / cookies / formulářů,
- jednoduchý replikující workflow v sandboxovém stylu.

Cílem je ukázat, jak taková architektura vypadá v kontrolovaném prostředí a jaké části kódu spolu souvisí.
