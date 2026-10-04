# DISCLAIMER / ETICKÉ A PRÁVNÍ HRANICE

**Tento repozitář je výhradně laboratorní výzkumný materiál.**

## Co to je
Vzdělávací proof-of-concept ukazující, jak vypadá řetěz *stored XSS →
keylogger → replikační smyčka* a — především — **jak se proti němu bránit**
(DEFENSE.md).

## Co to NENÍ a nesmí být
- **Není to nástroj k nasazení proti jakémukoli reálnému webu.**
- Veškerý testovací kód je záměrně inertní vůči veřejnému internetu:
  - host-guard povoluje spuštění jen na `lab.local` (neexistující doména,
    mapovaná lokálně v `/etc/hosts`),
  - C2 adresa je `127.0.0.1`,
  - samo-replikace je defaultně vypnutá (placeholder).
- **Změna těchto zábran a použití proti cizím systémům je NELEGÁLNÍ**
  (v ČR: §180 trestného činu neoprávněný přístup, §181 neoprávněný vnik,
  §232 poškozování cizích práv; obdobné zákony existují ve všech jurisdikcích).

## Souhlas a odpovědnost
- Používej výhradně na systémech, **které vlastníš**, nebo na kterých máš
  **písemné oprávnění** vlastníka (bug bounty scope, smlouva).
- Autor repozitáře neodpovídá za zneužití třetími stranami; stažení/klonování
  nezakládá oprávnění k testování cizích systémů.
- Zveřejnění má výzkumný a obranný účel: pochopit útok, aby se dal zastavit.

## If you are a defender
Jsi na správném místě: celý útok je zde rozebrán jako obranný case study.
Začni u **DEFENSE.md** — CSP, output escaping, HttpOnly, rate-limity a detekce.
