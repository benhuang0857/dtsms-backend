#!/bin/bash
# One-step certificate setup script with SAN support
# This follows the proper security flow

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================="
echo "Certificate Setup Script (with SAN)"
echo "=================================="
echo ""
echo "This script will generate certificates following security best practices:"
echo "  - Server generates its own certificates (with SAN)"
echo "  - Client generates its own private key and CSR"
echo "  - Server signs the client CSR"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

echo ""
echo "Starting certificate generation..."
echo "=================================="

# Step 1: Generate CA
echo ""
echo "Step 1/5: Generating CA certificate..."
cd webserver/certs
if [ ! -f "ca.key" ]; then
    openssl genrsa -out ca.key 2048
    MSYS_NO_PATHCONV=1 openssl req -new -x509 -days 365 -key ca.key -out ca.crt -subj "/CN=Local CA"
    echo "   ✓ CA certificate generated"
else
    echo "   ⚠ CA already exists, skipping..."
fi

# Step 2: Generate Server Certificate with SAN
echo ""
echo "Step 2/5: Generating server certificate with SAN..."
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
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt -days 365 -extensions v3_req -extfile server-san.cnf
rm -f server.csr server-san.cnf
echo "   ✓ Server certificate with SAN generated"

# Step 3: Generate client CSR
echo ""
echo "Step 3/5: Generating client CSR..."
cd ../../test-client/certs
./generate-csr.sh test-client

# Step 4: Sign client certificate
echo ""
echo "Step 4/5: Signing client certificate..."
cd ../../webserver/certs
./sign-client-cert.sh ../../test-client/certs/test-client.csr test-client

# Step 5: Rename for compatibility
echo ""
echo "Step 5/5: Setting up client certificates..."
cd ../../test-client/certs
[ -f client.key ] && rm -f client.key
[ -f client.crt ] && rm -f client.crt
mv test-client.key client.key
mv test-client.crt client.crt
rm -f test-client.csr

echo ""
echo "✓ Certificate setup complete!"

cd "$SCRIPT_DIR"

# Verify SAN
echo ""
echo "=================================="
echo "Verification:"
echo "=================================="
echo "Server certificate SAN:"
openssl x509 -in webserver/certs/server.crt -text -noout | grep -A 1 "Subject Alternative Name"

echo ""
echo "=================================="
echo "Next steps:"
echo "=================================="
echo ""
echo "1. Restart the services:"
echo "   cd webserver && docker-compose restart"
echo ""
echo "2. Test the upload:"
echo "   cd test-client"
echo "   python3 test-client.py upload/test.txt"
echo ""
echo "Generated certificates:"
echo "  Server: webserver/certs/server.{key,crt} (with SAN)"
echo "  Client: test-client/certs/client.{key,crt}"
echo "  CA:     webserver/certs/ca.crt"
echo ""
