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

# Check which method to use
echo "Choose setup method:"
echo "  1) Proper security flow (recommended)"
echo "  2) Quick development setup (generates client key on server - NOT SECURE)"
echo ""
read -p "Enter choice [1-2]: " choice

case $choice in
  1)
    echo ""
    echo "Using proper security flow..."
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
    echo "✓ Setup complete using proper security flow!"
    ;;

  2)
    echo ""
    echo "Using quick development setup..."
    echo "WARNING: This generates client private key on server!"
    echo "=================================="

    cd webserver/certs
    ./generate-certs.sh

    echo ""
    echo "✓ Setup complete using quick method!"
    ;;

  *)
    echo "Invalid choice. Exiting."
    exit 1
    ;;
esac

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
