#!/bin/bash

# Generate self-signed certificates for local development with LAN support
mkdir -p certs

# Get local IP address (macOS)
LOCAL_IP=$(ifconfig en0 | grep "inet " | awk '{print $2}' 2>/dev/null)
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP=$(ifconfig en1 | grep "inet " | awk '{print $2}' 2>/dev/null)
fi

if [ -z "$LOCAL_IP" ]; then
    echo "Could not detect local IP address. Please check your network interface."
    echo "Common interfaces: en0 (WiFi), en1 (Ethernet)"
    echo "Manual check: ifconfig | grep 'inet '"
    exit 1
fi

echo "Detected local IP: $LOCAL_IP"

# Create certificate config with Subject Alternative Names
cat > certs/server.conf << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C=US
ST=CA
L=San Francisco
O=Development
CN=localhost

[v3_req]
basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.local
IP.1 = 127.0.0.1
IP.2 = ::1
IP.3 = $LOCAL_IP
EOF

# Generate private key
openssl genrsa -out certs/server.key 2048

# Generate certificate with SAN extensions
openssl req -new -x509 -key certs/server.key -out certs/server.crt -days 365 -config certs/server.conf -extensions v3_req

echo "Certificates generated in ./certs/"
echo "Certificate includes:"
echo "  - localhost"
echo "  - 127.0.0.1"
echo "  - $LOCAL_IP (your LAN IP)"
echo ""
echo "For iOS testing:"
echo "1. Access https://$LOCAL_IP:8000 on your iPhone"
echo "2. Accept the self-signed certificate warning"
echo "3. Camera should work over HTTPS"
