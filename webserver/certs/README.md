# Server Certificates

This directory contains SSL/TLS certificates for the TCP server with mTLS support.

**IMPORTANT**: Certificates are NOT tracked in Git for security reasons. You must generate them on each new machine.

## Files (not in Git)

- `ca.key` - Certificate Authority private key (KEEP SECRET!)
- `ca.crt` - Certificate Authority certificate
- `ca.srl` - Serial number tracking file (auto-generated)
- `server.key` - Server private key (KEEP SECRET!)
- `server.crt` - Server certificate (CN=localhost)

## Quick Setup

### Step 1: Generate Server Certificates

```bash
./generate-server-certs.sh
```

This will:
1. Generate CA certificate (ca.key, ca.crt)
2. Generate server certificate (server.key, server.crt) with CN=localhost

### Step 2: Sign Client Certificates

When a client requests a certificate:

1. **Client generates CSR**:
   ```bash
   cd test-client/certs
   ./generate-csr.sh test-client
   ```

2. **Server signs the CSR**:
   ```bash
   cd webserver/certs
   ./sign-client-cert.sh ../../test-client/certs/test-client.csr test-client
   ```

3. **Client renames for compatibility**:
   ```bash
   cd test-client/certs
   mv test-client.key client.key
   mv test-client.crt client.crt
   ```

### Quick Development Setup (Legacy)

For local development only:

```bash
./generate-certs.sh
```

**WARNING**: This generates the client private key on the server, which violates security best practices!

### Manual Generation (if needed)

If you need to customize the certificate generation:

#### 1. Generate CA
```bash
openssl genrsa -out ca.key 2048
openssl req -new -x509 -days 365 -key ca.key -out ca.crt \
  -subj "//CN=Local CA"
```

#### 2. Generate Server Certificate
```bash
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
  -subj "//CN=localhost"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 365
rm server.csr
```

#### 3. Generate Client Certificate
```bash
cd ../../test-client/certs
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr \
  -subj "//CN=test-client"
openssl x509 -req -in client.csr -CA ../../webserver/certs/ca.crt \
  -CAkey ../../webserver/certs/ca.key -CAcreateserial \
  -out client.crt -days 365
cp ../../webserver/certs/ca.crt .
rm client.csr
```

## Server Configuration

The server is configured to use mTLS (mutual TLS authentication) by default:

```python
# In server.py
TLS_ENABLE = True
TLS_CERT = "/certs/server.crt"
TLS_KEY = "/certs/server.key"
TLS_CA = "/certs/ca.crt"
```

## Production Use

**WARNING**: These are self-signed certificates for development/testing only!

For production:
1. Obtain certificates from a trusted Certificate Authority (Let's Encrypt, etc.)
2. Use proper certificate management tools
3. Set up certificate rotation
4. Never commit private keys to version control
5. Use proper secrets management (HashiCorp Vault, AWS Secrets Manager, etc.)

## Troubleshooting

### Certificate hostname mismatch
If you see "IP address mismatch" errors, make sure to use `localhost` instead of `127.0.0.1` when connecting, as the server certificate CN is set to `localhost`.

### SSL handshake failed
Ensure all three files exist: `server.crt`, `server.key`, and `ca.crt`.

### Client cannot connect
The client also needs certificates in `test-client/certs/`. Run `./generate-certs.sh` to generate them.
