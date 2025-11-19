#!/bin/bash
# One-step certificate setup script
# This follows the proper security flow

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================="
echo "Certificate Setup Script"
echo "=================================="
echo ""
echo "This script will generate certificates following security best practices:"
echo "  - Server generates its own certificates"
echo "  - Client generates its own private key and CSR"
echo "  - Server signs the client CSR"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

echo ""
echo "Starting certificate generation..."
echo "=================================="

# Step 1: Generate server certificates
echo ""
echo "Step 1/4: Generating server certificates..."
cd webserver/certs
./generate-server-certs.sh

# Step 2: Generate client CSR
echo ""
echo "Step 2/4: Generating client CSR..."
cd ../../test-client/certs
./generate-csr.sh test-client

# Step 3: Sign client certificate
echo ""
echo "Step 3/4: Signing client certificate..."
cd ../../webserver/certs
./sign-client-cert.sh ../../test-client/certs/test-client.csr test-client

# Step 4: Rename for compatibility
echo ""
echo "Step 4/4: Setting up client certificates..."
cd ../../test-client/certs
[ -f client.key ] && rm -f client.key
[ -f client.crt ] && rm -f client.crt
mv test-client.key client.key
mv test-client.crt client.crt
rm -f test-client.csr

echo ""
echo "✓ Certificate setup complete!"

cd "$SCRIPT_DIR"

echo ""
echo "=================================="
echo "Next steps:"
echo "=================================="
echo ""
echo "1. Start/restart the services:"
echo "   docker-compose restart"
echo ""
echo "2. Test the upload:"
echo "   cd test-client"
echo "   python test-client.py upload/test.txt"
echo ""
echo "Generated certificates:"
echo "  Server: webserver/certs/server.{key,crt}"
echo "  Client: test-client/certs/client.{key,crt}"
echo "  CA:     webserver/certs/ca.crt"
echo ""
