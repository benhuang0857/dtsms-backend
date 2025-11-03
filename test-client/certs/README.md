# Client Certificates

This directory contains the client certificates used for mTLS authentication with the TCP server.

**IMPORTANT**: Certificates are NOT tracked in Git for security reasons. You must generate them on each new machine.

## Files (not in Git)

- `client.crt` - Client certificate
- `client.key` - Client private key (KEEP SECRET!)
- `ca.crt` - Certificate Authority certificate (for verifying server certificate)

## Quick Start

### Proper Flow (Recommended for Production-like Setup)

1. **Generate client private key and CSR**:
   ```bash
   cd test-client/certs
   ./generate-csr.sh test-client
   ```
   This creates:
   - `test-client.key` (KEEP SECRET - stays on client)
   - `test-client.csr` (send to CA/Server for signing)

2. **Get CSR signed by CA** (on server):
   ```bash
   cd webserver/certs
   ./sign-client-cert.sh ../../test-client/certs/test-client.csr test-client
   ```
   This creates:
   - `test-client.crt` (signed certificate)
   - Copies `ca.crt` to client directory

3. **Rename files** (for compatibility):
   ```bash
   cd test-client/certs
   mv test-client.key client.key
   mv test-client.crt client.crt
   ```

### Quick Setup (Development Only)

For local development, you can use the legacy script:

```bash
cd webserver/certs
./generate-certs.sh
```

**WARNING**: This generates the client private key on the server, which is not secure for production!

## Usage

The test-client.py script will automatically use these certificates if they exist in this directory.

### Simple usage (auto-detects certificates):
```bash
python test-client.py upload/test.txt
```

### With custom certificate paths:
```bash
python test-client.py upload/test.txt \
  --client-cert /path/to/client.crt \
  --client-key /path/to/client.key \
  --ca-cert /path/to/ca.crt
```

### Without TLS (not recommended for production):
```bash
python test-client.py upload/test.txt --no-tls
```

## Generating New Certificates

If you need to generate new client certificates, use the following commands:

```bash
# Generate client private key
openssl genrsa -out client.key 2048

# Generate certificate signing request
openssl req -new -key client.key -out client.csr -subj "//CN=test-client"

# Sign with CA certificate (located in webserver/certs)
openssl x509 -req -in client.csr -CA ../webserver/certs/ca.crt \
  -CAkey ../webserver/certs/server.key -CAcreateserial \
  -out client.crt -days 365

# Copy CA certificate for server verification
cp ../webserver/certs/ca.crt .
```

## Security Notes

- Keep the `client.key` file secure and never commit it to version control
- The certificates are currently self-signed for development purposes
- For production use, obtain certificates from a trusted Certificate Authority
