#!/bin/bash
# Clean all certificates script
# This will remove all generated certificates from server and client

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================="
echo "Certificate Cleanup Script"
echo "=================================="
echo ""
echo "This script will delete ALL certificates:"
echo "  - Server certificates (webserver/certs/)"
echo "  - Client certificates (test-client/certs/)"
echo "  - Temporary configuration files"
echo ""
echo "⚠️  WARNING: This action cannot be undone!"
echo ""
read -p "Are you sure you want to delete all certificates? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled. No certificates were deleted."
    exit 0
fi

echo ""
echo "Starting certificate cleanup..."
echo "=================================="

# Clean server certificates
echo ""
echo "Cleaning server certificates..."
cd webserver/certs
rm -f ca.key ca.crt ca.srl
rm -f server.key server.crt server.csr
rm -f server-san.cnf
echo "   ✓ Server certificates deleted"

# Clean client certificates
echo ""
echo "Cleaning client certificates..."
cd ../../test-client/certs
rm -f client.key client.crt client.csr
rm -f test-client.key test-client.crt test-client.csr
rm -f ca.crt
echo "   ✓ Client certificates deleted"

cd "$SCRIPT_DIR"

echo ""
echo "✓ Certificate cleanup complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "  1. Regenerate certificates: ./setup-certificates.sh"
echo "  2. Restart services: cd webserver && docker-compose restart"
echo ""
