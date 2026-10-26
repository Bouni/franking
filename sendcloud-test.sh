#!/usr/bin/env bash
# List the Sendcloud shipping options available for a shipment from DE.
#
# Usage: ./sendcloud-test.sh [country] [weight_g] [--all]
#   ./sendcloud-test.sh            -> Warenpost options to CH, 300g
#   ./sendcloud-test.sh AT 500     -> Warenpost options to AT, 500g
#   ./sendcloud-test.sh CH 300 --all -> all options to CH

set -euo pipefail

cd "$(dirname "$0")"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${SENDCLOUD_PUBLIC_KEY:?SENDCLOUD_PUBLIC_KEY not set}"
: "${SENDCLOUD_PRIVATE_KEY:?SENDCLOUD_PRIVATE_KEY not set}"

COUNTRY="${1:-CH}"
WEIGHT="${2:-300}"

if [[ "${3:-}" == "--all" ]]; then
  FILTER='.data[] | {code, name, carrier: .carrier.code}'
else
  FILTER='.data[] | select(.name | test("warenpost"; "i")) | {code, name, carrier: .carrier.code}'
fi

curl -s -u "$SENDCLOUD_PUBLIC_KEY:$SENDCLOUD_PRIVATE_KEY" \
  -H "Content-Type: application/json" \
  -X POST https://panel.sendcloud.sc/api/v3/shipping-options \
  -d "{\"from_country_code\":\"DE\",\"to_country_code\":\"$COUNTRY\",\"weight\":{\"value\":$WEIGHT,\"unit\":\"g\"}}" \
  | jq "$FILTER"
