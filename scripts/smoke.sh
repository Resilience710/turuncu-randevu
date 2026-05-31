#!/usr/bin/env bash
# Render deploy sonrası hızlı smoke test.
# Kullanım: API_BASE=https://turuncu-api.onrender.com ./scripts/smoke.sh

set -euo pipefail
API="${API_BASE:-http://localhost:8000}/api"
echo "→ API: $API"

step() { echo; echo "▶ $1"; }

step "1) Health"
curl -fsS "$API/" | head -c 200; echo

step "2) Sectors"
curl -fsS "$API/sectors" | head -c 300; echo

step "3) KVKK metni"
curl -fsS "$API/kvkk-text" | head -c 200; echo

step "4) İşletme listesi (TEST123 seed'i görünmeli)"
curl -fsS "$API/businesses" | head -c 500; echo

step "5) Müşteri OTP iste (dev fallback ile)"
ts=$(date +%s)
PHONE="0532${ts:6:7}"
GMAIL="smoke${ts}@example.com"
RESP=$(curl -fsS -X POST "$API/auth/customer/request-otp" \
  -H "Content-Type: application/json" \
  -d "{\"first_name\":\"Smoke\",\"last_name\":\"Test\",\"phone\":\"$PHONE\",\"gmail\":\"$GMAIL\",\"password\":\"1234\",\"kvkk_accepted\":true}")
echo "$RESP"
DEV_OTP=$(echo "$RESP" | python -c "import sys,json;print(json.load(sys.stdin).get('dev_otp_code',''))")

if [ -n "$DEV_OTP" ]; then
  step "6) Doğrulama (dev OTP: $DEV_OTP)"
  curl -fsS -X POST "$API/auth/customer/verify-register" \
    -H "Content-Type: application/json" \
    -d "{\"phone\":\"$PHONE\",\"gmail\":\"$GMAIL\",\"otp_code\":\"$DEV_OTP\"}"
  echo
else
  echo "  ! Netgsm yapılandırıldığı için OTP SMS ile geldi — manuel doğrulama gerek"
fi

step "7) Patron login (testpatron@gmail.com / 1234)"
OWNER_RESP=$(curl -fsS -X POST "$API/auth/owner/login" \
  -H "Content-Type: application/json" \
  -d '{"identifier":"testpatron@gmail.com","password":"1234"}')
OWNER_TOKEN=$(echo "$OWNER_RESP" | python -c "import sys,json;print(json.load(sys.stdin)['token'])")
echo "  token: ${OWNER_TOKEN:0:20}…"

step "8) /me (patron)"
curl -fsS "$API/me" -H "Authorization: Bearer $OWNER_TOKEN" | head -c 400; echo

step "9) Occupancy"
curl -fsS "$API/stations/occupancy" -H "Authorization: Bearer $OWNER_TOKEN" | head -c 400; echo

echo
echo "✓ Smoke test başarılı."
