#!/bin/bash
# Generate client private key and Certificate Signing Request (CSR)
# The CSR should be sent to the CA/Server for signing

set -e

CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$CERT_DIR"

CLIENT_NAME="${1:-test-client}"

echo "Generating client certificate request..."
echo "======================================="
echo "Client name: $CLIENT_NAME"
echo ""

# 1. Generate private key (STAYS ON CLIENT!)
if [ -f "${CLIENT_NAME}.key" ]; then
    echo "Warning: ${CLIENT_NAME}.key already exists"
    read -p "Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
fi

echo "1. Generating private key..."
openssl genrsa -out "${CLIENT_NAME}.key" 2048
chmod 600 "${CLIENT_NAME}.key"
echo "   ✓ Private key generated: ${CLIENT_NAME}.key"

# 2. Generate CSR
echo "2. Generating Certificate Signing Request (CSR)..."
openssl req -new -key "${CLIENT_NAME}.key" -out "${CLIENT_NAME}.csr" \
  -subj "//CN=${CLIENT_NAME}"
echo "   ✓ CSR generated: ${CLIENT_NAME}.csr"

echo ""
echo "✓ Certificate request generated!"
echo "======================================="
echo "Next steps:"
echo ""
echo "Option A - Local CA (development):"
echo "  Send the CSR to the CA/Server admin:"
echo "    ${CLIENT_NAME}.csr"
echo ""
echo "  Server admin should run:"
echo "    cd ../../webserver/certs"
echo "    ./sign-client-cert.sh $CERT_DIR/${CLIENT_NAME}.csr ${CLIENT_NAME}"
echo ""
echo "Option B - Quick setup (development only):"
echo "  cd ../../webserver/certs"
echo "  ./sign-client-cert.sh $CERT_DIR/${CLIENT_NAME}.csr ${CLIENT_NAME}"
echo ""
echo "SECURITY NOTE:"
echo "  - Keep ${CLIENT_NAME}.key PRIVATE and SECURE"
echo "  - Never send the .key file, only send the .csr file"
echo "  - After receiving the signed certificate, you'll have:"
echo "    * ${CLIENT_NAME}.key (private key - KEEP SECRET)"
echo "    * ${CLIENT_NAME}.crt (signed certificate)"
echo "    * ca.crt (CA certificate)"
echo ""
