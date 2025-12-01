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
      -subj "/CN=Local CA"
    echo "   ✓ CA certificate generated"
else
    echo "1. CA certificate already exists (skipping)"
fi

# 2. Generate Server Certificate with SAN
echo "2. Generating server certificate with SAN..."

# Create SAN configuration file
cat > server-san.cnf << 'EOF'
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = localhost

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
IP.1 = 127.0.0.1
EOF

openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -config server-san.cnf
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 365 \
  -extensions v3_req -extfile server-san.cnf
rm -f server.csr server-san.cnf
echo "   ✓ Server certificate generated (with SAN)"

echo ""
echo "✓ Server setup complete!"
echo "======================================="
echo "Generated files:"
echo "  CA:     $CERT_DIR/ca.{key,crt}"
echo "  Server: $CERT_DIR/server.{key,crt}"
echo ""
echo "Verifying SAN in server certificate:"
openssl x509 -in server.crt -text -noout | grep -A 1 "Subject Alternative Name" || echo "  WARNING: SAN not found!"
echo ""
echo "Next steps:"
echo "  1. Keep ca.key SECURE - it's used to sign all certificates"
echo "  2. Clients should use 'sign-client-cert.sh' to get their certificates signed"
echo "  3. Share ca.crt with clients (for server verification)"
echo ""
