#!/bin/bash
# Generate server certificates and CA for mTLS
# Client certificates should be requested separately

set -e

CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$CERT_DIR"

echo "Generating server certificates in: $CERT_DIR"
echo "======================================="

# 1. Generate CA (Certificate Authority)
if [ ! -f "ca.key" ]; then
    echo "1. Generating CA certificate..."
    openssl genrsa -out ca.key 2048
    openssl req -new -x509 -days 365 -key ca.key -out ca.crt \
      -subj "//CN=Local CA"
    echo "   ✓ CA certificate generated"
else
    echo "1. CA certificate already exists (skipping)"
fi

# 2. Generate Server Certificate
echo "2. Generating server certificate..."
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
  -subj "//CN=localhost"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 365
rm -f server.csr
echo "   ✓ Server certificate generated"

echo ""
echo "✓ Server setup complete!"
echo "======================================="
echo "Generated files:"
echo "  CA:     $CERT_DIR/ca.{key,crt}"
echo "  Server: $CERT_DIR/server.{key,crt}"
echo ""
echo "Next steps:"
echo "  1. Keep ca.key SECURE - it's used to sign all certificates"
echo "  2. Clients should use 'sign-client-cert.sh' to get their certificates signed"
echo "  3. Share ca.crt with clients (for server verification)"
echo ""
