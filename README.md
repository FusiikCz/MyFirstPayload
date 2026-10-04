# LAB — mock prostředí

Izolovaný mock web (zranitelná i zabezpečená varianta) pro bezpečné studium
celého řetězu. Nic z toho nesmí směřovat na veřejný internet.

## Spuštění (5 minut)

```bash
# 1) mapování lab hosta (Linux/mac: /etc/hosts, Windows: drivers\etc\hosts)
127.0.0.1   lab.local

# 2) mock web (vyžaduje php + php-gd)
cd lab && php -S 0.0.0.0:8000

# 3) C2 (jiný terminál)
python3 c2.py          # vypíše TOKEN

# 4) prohlížeč: http://lab.local:8000  (VULNERABLE)  /  ?safe=1 (PATCHED)
```

## Testovací scénář

1. **VULNERABLE režim:** vlož payload z `payload_lab.txt` do pole "Text",
   odešli (zadej správný součet captchy), otevři vytvořený inzerát
   → v prohlížeči se spustí JS, události přibývají v C2 dashboardu.
2. **PATCHED režim:** přepni na `?safe=1`, vlož stejný payload
   → payload se zobrazí jako text, nespustí se (escapování + CSP).
3. **Replikace:** použij payload z `worm_lab.txt`, po beaconu zavolej
   `curl "http://127.0.0.1:8080/spread?token=<TOKEN>"`
   → červ řeší captchu přes C2 `/solve` a vkládá nové inzeráty na mock webu.
4. **Měření:** `/export?token=<TOKEN>` → JSON pro analýzu (rychlost šíření,
   úspěšnost OCR, efekt rate-limitu).

## Automatický self-test (bez prohlížeče)

`test_c2.sh` ověří celý C2 řetěz na loopbacku a sám se uklidí:

```bash
bash lab/test_c2.sh
# testuje: ochrana tokenem (401/200), /hello /k /p /f (204),
#          beacon -> spread -> beacon (SPREAD/Consumed),
#          /solve OCR proti PIL vzorku z gen_captcha.py,
#          /export obsahuje události
# očekávaný výstup: PASS=10 FAIL=0
```

`gen_captcha.py` vygeneruje vzorovou captchu (stejný styl jako `captcha.php`)
do `/tmp/cap_lab.jpg` a ground-truth do `/tmp/cap_lab.info` — používá se v self-testu.

Pozn.: `/solve` očekává obrázek jako base64 v query (`?img=`); v URL je nutné
base64 URL-enkódovat (`curl -G --data-urlencode`), jinak `+` rozbije query string.

## Co si všímat (research notes)

- OCR má ~70–85 % úspěšnost na první dvě číslice; měř, kolik replikací
  selže (payload bez retry se "ticho" zastaví).
- CSP v PATCHED režimu zablokuje `onerror` i XHR na C2 — to je hlavní obrana.
- HttpOnly cookie v mocku nenastavujeme; v DEFENSE.md je přesný postup,
  jak ji nasadit v reálné aplikaci.
