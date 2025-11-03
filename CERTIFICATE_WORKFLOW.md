# Certificate Management Workflow

This document explains the proper certificate management flow for mTLS authentication.

## 🔐 Security Principles

1. **Private keys NEVER leave their origin machine**
2. **Only CSRs (Certificate Signing Requests) are transmitted**
3. **CA private key is highly protected**
4. **Each environment has its own certificates**

## 📊 Certificate Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    CA / Server Side                          │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 1. Generate CA (ONE TIME)                          │     │
│  │    ./generate-server-certs.sh                      │     │
│  │    Creates: ca.key (KEEP SECRET!), ca.crt          │     │
│  └────────────────────────────────────────────────────┘     │
│                           │                                   │
│  ┌────────────────────────▼───────────────────────────┐     │
│  │ 2. Generate Server Certificate                     │     │
│  │    Creates: server.key, server.crt                 │     │
│  └────────────────────────────────────────────────────┘     │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           │ ca.crt (public, shareable)
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      Client Side                             │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 3. Generate Client Private Key & CSR              │     │
│  │    ./generate-csr.sh test-client                  │     │
│  │    Creates:                                        │     │
│  │    - test-client.key (STAYS ON CLIENT!)           │     │
│  │    - test-client.csr (send to CA)                 │     │
│  └────────────────────────────────────────────────────┘     │
│                           │                                   │
│                           │ test-client.csr (send to CA)     │
│                           ▼                                   │
└─────────────────────────────────────────────────────────────┘
                           │
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    CA / Server Side                          │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 4. Sign Client CSR                                 │     │
│  │    ./sign-client-cert.sh client.csr test-client   │     │
│  │    Creates: test-client.crt                        │     │
│  └────────────────────────────────────────────────────┘     │
│                           │                                   │
│                           │ test-client.crt + ca.crt         │
│                           ▼                                   │
└─────────────────────────────────────────────────────────────┘
                           │
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      Client Side                             │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 5. Client Now Has Complete Certificates           │     │
│  │    - test-client.key (private key)                │     │
│  │    - test-client.crt (signed certificate)         │     │
│  │    - ca.crt (to verify server)                    │     │
│  └────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │ 6. Connect to Server with mTLS                     │     │
│  │    python test-client.py upload/file.txt           │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Step-by-Step Setup

### Server Administrator

#### 1. Initial CA and Server Setup (ONE TIME)
```bash
cd webserver/certs
./generate-server-certs.sh
```

**Creates**:
- `ca.key` - CA private key (CRITICAL: Keep this secure!)
- `ca.crt` - CA certificate (share with clients)
- `server.key` - Server private key
- `server.crt` - Server certificate

#### 2. Sign Client Certificate Requests (PER CLIENT)
When a client sends you their CSR:

```bash
cd webserver/certs
./sign-client-cert.sh /path/to/client.csr client-name
```

**Creates**:
- `client-name.crt` - Signed client certificate (send back to client)
- Copies `ca.crt` to client directory

### Client User

#### 1. Generate Private Key and CSR
```bash
cd test-client/certs
./generate-csr.sh test-client
```

**Creates**:
- `test-client.key` - Private key (KEEP SECRET, NEVER SEND!)
- `test-client.csr` - Certificate signing request (send to CA)

#### 2. Send CSR to CA/Server Admin
Send only the `.csr` file:
```bash
# Example: via email, secure file transfer, etc.
scp test-client.csr admin@server:/tmp/
```

#### 3. Receive Signed Certificate
Server admin will send back:
- `test-client.crt` - Your signed certificate
- `ca.crt` - CA certificate

#### 4. Setup for Use
```bash
cd test-client/certs
mv test-client.key client.key
mv test-client.crt client.crt
# ca.crt is already in place
```

#### 5. Connect to Server
```bash
cd test-client
python test-client.py upload/test.txt
```

## 🔒 Security Best Practices

### DO ✅
- Keep private keys (*.key) secure and never transmit them
- Generate private keys on the machine where they'll be used
- Use strong permissions: `chmod 600 *.key`
- Regenerate certificates periodically
- Use separate certificates for each environment (dev/staging/prod)
- Backup CA private key in a secure location

### DON'T ❌
- Never commit private keys to version control
- Never send private keys over email/chat
- Never generate client private keys on the server
- Never share CA private key
- Never use the same certificates across environments
- Never skip certificate validation in production

## 🏭 Production vs Development

### Production
- Use certificates from a trusted CA (Let's Encrypt, DigiCert, etc.)
- Implement certificate rotation
- Use hardware security modules (HSM) for CA key
- Monitor certificate expiration
- Have proper key management procedures

### Development (Current Setup)
- Self-signed certificates are acceptable
- Can use `generate-certs.sh` for quick local testing
- Still follow the CSR flow to practice good habits
- Never use development certificates in production

## 🆘 Troubleshooting

### "Certificate verify failed"
- Ensure client has the correct `ca.crt`
- Check certificate expiration dates
- Verify CN matches hostname (use `localhost` not `127.0.0.1`)

### "SSL handshake failed"
- Ensure all required files exist (client.key, client.crt, ca.crt)
- Check file permissions
- Verify server is using mTLS mode

### "IP address mismatch"
- Server certificate CN is `localhost`
- Use `localhost` instead of `127.0.0.1` when connecting

## 📚 Additional Resources

- [OpenSSL Documentation](https://www.openssl.org/docs/)
- [mTLS Best Practices](https://www.cloudflare.com/learning/access-management/what-is-mutual-tls/)
- [Certificate Management](https://smallstep.com/blog/everything-pki/)
