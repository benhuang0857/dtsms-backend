#!/bin/bash
# Generate self-signed certificates for development/testing

set -e

CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$CERT_DIR"

echo "Generating certificates in: $CERT_DIR"
echo "======================================="

# 1. Generate CA (Certificate Authority)
echo "1. Generating CA certificate..."
openssl genrsa -out ca.key 2048
openssl req -new -x509 -days 365 -key ca.key -out ca.crt \
  -subj "//CN=Local CA"

# 2. Generate Server Certificate
echo "2. Generating server certificate..."
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
  -subj "//CN=localhost"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 365

# 3. Generate Client Certificate
echo "3. Generating client certificate..."
CLIENT_CERT_DIR="../../test-client/certs"
mkdir -p "$CLIENT_CERT_DIR"

openssl genrsa -out "$CLIENT_CERT_DIR/client.key" 2048
openssl req -new -key "$CLIENT_CERT_DIR/client.key" -out "$CLIENT_CERT_DIR/client.csr" \
  -subj "//CN=test-client"
openssl x509 -req -in "$CLIENT_CERT_DIR/client.csr" -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out "$CLIENT_CERT_DIR/client.crt" -days 365

# Copy CA cert to client directory
cp ca.crt "$CLIENT_CERT_DIR/"

# Clean up CSR files
rm -f server.csr "$CLIENT_CERT_DIR/client.csr"

echo ""
echo "✓ Certificate generation complete!"
echo "======================================="
echo "Generated files:"
echo "  Server: $CERT_DIR/server.{key,crt}"
echo "  Client: $CLIENT_CERT_DIR/client.{key,crt}"
echo "  CA:     $CERT_DIR/ca.crt (copied to client)"
echo ""
echo "Note: These are self-signed certificates for development only."
echo "      Do NOT use in production!"
