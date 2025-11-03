#!/bin/bash
# Sign a client certificate request (CSR)
# Client should generate their own private key and CSR, then send CSR to be signed

set -e

CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <client.csr> [client-name]"
    echo ""
    echo "Example:"
    echo "  $0 /path/to/client.csr test-client"
    echo ""
    echo "This will generate:"
    echo "  - client.crt (signed certificate)"
    echo "  - ca.crt (for client to verify server)"
    exit 1
fi

CSR_FILE="$1"
CLIENT_NAME="${2:-client}"
OUTPUT_DIR="$(dirname "$CSR_FILE")"

if [ ! -f "$CSR_FILE" ]; then
    echo "Error: CSR file not found: $CSR_FILE"
    exit 1
fi

if [ ! -f "$CERT_DIR/ca.key" ] || [ ! -f "$CERT_DIR/ca.crt" ]; then
    echo "Error: CA certificates not found. Run generate-server-certs.sh first."
    exit 1
fi

cd "$CERT_DIR"

echo "Signing client certificate..."
echo "======================================="
echo "CSR file:    $CSR_FILE"
echo "Client name: $CLIENT_NAME"
echo ""

# Sign the CSR
openssl x509 -req -in "$CSR_FILE" \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out "$OUTPUT_DIR/${CLIENT_NAME}.crt" -days 365

# Copy CA certificate to client directory
cp ca.crt "$OUTPUT_DIR/"

echo ""
echo "✓ Client certificate signed successfully!"
echo "======================================="
echo "Generated files:"
echo "  Certificate: $OUTPUT_DIR/${CLIENT_NAME}.crt"
echo "  CA cert:     $OUTPUT_DIR/ca.crt"
echo ""
echo "Client should now have:"
echo "  - ${CLIENT_NAME}.key (kept private on client)"
echo "  - ${CLIENT_NAME}.crt (signed certificate)"
echo "  - ca.crt (to verify server)"
echo ""
