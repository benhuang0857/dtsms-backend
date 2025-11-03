# Quick Setup Guide

## 🚀 First Time Setup

### Option 1: One-Command Setup (Recommended)

Run the automated setup script:

```bash
./setup-certificates.sh
```

Choose your preferred method:
1. **Proper security flow** - Client private key stays on client (recommended)
2. **Quick development** - All certificates generated in one place (faster, less secure)

### Option 2: Manual Setup

#### For Production-like Environment (Secure)

```bash
# 1. Generate server certificates
cd webserver/certs
./generate-server-certs.sh

# 2. Generate client CSR
cd ../../test-client/certs
./generate-csr.sh

# 3. Sign client certificate
cd ../../webserver/certs
./sign-client-cert.sh ../../test-client/certs/test-client.csr test-client

# 4. Rename for compatibility
cd ../../test-client/certs
mv test-client.key client.key
mv test-client.crt client.crt
```

#### For Quick Development (Simple)

```bash
cd webserver/certs
./generate-certs.sh
```

## 🔄 After Generating Certificates

### Start the Services

```bash
# If first time
docker-compose up -d

# If already running
docker-compose restart
```

### Test the Upload

```bash
cd test-client
python test-client.py upload/test.txt
```

## 📁 Project Structure

```
dtsms-backend/
├── setup-certificates.sh          # One-command setup
├── CERTIFICATE_WORKFLOW.md        # Detailed certificate flow
│
├── webserver/
│   ├── certs/
│   │   ├── generate-server-certs.sh  # Generate CA + Server cert
│   │   ├── sign-client-cert.sh       # Sign client CSR
│   │   ├── generate-certs.sh         # Quick all-in-one (dev only)
│   │   ├── ca.{key,crt}              # CA certificates (not in git)
│   │   └── server.{key,crt}          # Server certificates (not in git)
│   └── docker-compose.yml
│
└── test-client/
    ├── certs/
    │   ├── generate-csr.sh           # Generate client key + CSR
    │   ├── client.{key,crt}          # Client certificates (not in git)
    │   └── ca.crt                    # CA cert (not in git)
    └── test-client.py                # Upload client
```

## 🔐 Security Notes

- All certificates (*.key, *.crt) are in `.gitignore`
- Certificates must be generated on each new machine
- Private keys never leave their origin machine (in proper flow)
- For production: use certificates from a trusted CA

## 🆘 Troubleshooting

### Certificate not found

Make sure you've run the certificate setup:
```bash
./setup-certificates.sh
```

### Permission denied

Make scripts executable:
```bash
chmod +x setup-certificates.sh
chmod +x webserver/certs/*.sh
chmod +x test-client/certs/*.sh
```

### Connection refused

1. Check if server is running:
   ```bash
   docker ps | grep tcp-server
   ```

2. Check server logs:
   ```bash
   docker logs uvloop-tcp-server
   ```

### SSL handshake failed

1. Regenerate all certificates:
   ```bash
   rm -f webserver/certs/*.{key,crt,srl}
   rm -f test-client/certs/*.{key,crt,csr}
   ./setup-certificates.sh
   docker-compose restart
   ```

2. Make sure to use `localhost` not `127.0.0.1`

## 📚 More Information

- [CERTIFICATE_WORKFLOW.md](./CERTIFICATE_WORKFLOW.md) - Detailed certificate management flow
- [webserver/certs/README.md](./webserver/certs/README.md) - Server certificate details
- [test-client/certs/README.md](./test-client/certs/README.md) - Client certificate details
