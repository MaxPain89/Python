#!/usr/bin/env bash

set -e
set -o xtrace

#---------------------------- Install required soft -----------------------
sudo apt-get update
sudo apt-get install openvpn easy-rsa expect -y
make-cadir ~/openvpn-ca
cd ~/openvpn-ca
#------------------------------------------------------------------------

#---------------------------- Set predefined vars -----------------------
sed -i 's/export KEY_ORG="Fort-Funston"/export KEY_ORG="PersonalVPNServer"/g' vars
sed -i 's/export KEY_EMAIL="me@myhost.mydomain"/export KEY_EMAIL="admin@example.com"/g' vars
sed -i 's/export KEY_OU="MyOrganizationalUnit"/export KEY_OU="VPNUnit"/g' vars
sed -i 's/export KEY_NAME="EasyRSA"/export KEY_NAME="server"/g' vars
#------------------------------------------------------------------------

#---------------------------- Set predefined vars -----------------------
source vars
./clean-all
#------------------------------------------------------------------------

#-----------------------------Create ca certificates-----------------------
cat >build-ca.exp <<EOF
#!/usr/bin/expecf
set timeout -1
spawn ./build-ca
expect "Country Name (2 letter code) \\\\\[US]:"
send -- "US\r"
expect "State or Province Name (full name) \\\\\[CA]:"
send -- "NY\r"

expect "Locality Name (eg, city) \\\\\[SanFrancisco]:"
send -- "New York City\r"

expect "Organization Name (eg, company) \\\\\[PersonalVPNServer]:"
send -- "MyOrganization\r"

expect "Organizational Unit Name (eg, section) \\\\\[VPNUnit]:"
send -- "IT\r"

expect "Common Name (eg, your name or your server's hostname) \\\\\[PersonalVPNServer CA]:"
send -- "myServer.example.com\r"

expect "Name \\\\\[server]:"
send -- "MyServer\r"

expect "Email Address \\\\\[admin@example.com]:"
send -- "myemail@example.com\r"
expect eof

EOF

expect build-ca.exp
#------------------------------------------------------------------------

#-------------------------Create server key------------------------------
cat >build-key-server.exp <<EOF
#!/usr/bin/expecf
set timeout -1
spawn ./build-key-server server
expect "Country Name (2 letter code) \\\\\[US]:"
send -- "\r"
expect "State or Province Name (full name) \\\\\[CA]:"
send -- "\r"

expect "Locality Name (eg, city) \\\\\[SanFrancisco]:"
send -- "\r"

expect "Organization Name (eg, company) \\\\\[PersonalVPNServer]:"
send -- "\r"

expect "Organizational Unit Name (eg, section) \\\\\[VPNUnit]:"
send -- "\r"

expect "Common Name (eg, your name or your server's hostname) \\\\\[server]:"
send -- "\r"

expect "Name \\\\\[server]:"
send -- "\r"

expect "Email Address \\\\\[admin@example.com]:"
send -- "\r"

expect "A challenge password \\\\\[]:"
send -- "\r"

expect "An optional company name \\\\\[]:"
send -- "\r"

expect "Sign the certificate? \\\\\[y/n]:"
send -- "y\r"

expect "1 out of 1 certificate requests certified, commit? \\\\\[y/n]"
send -- "y\r"

expect eof

EOF

expect build-key-server.exp
#------------------------------------------------------------------------

#----Use dh algorithm for strong cipher and generate HMAC signature------
./build-dh
openvpn --genkey --secret keys/ta.key
#------------------------------------------------------------------------

#------------------Create client key-------------------------------------
cat >build-client-key.exp <<EOF
#!/usr/bin/expecf
set timeout -1
spawn ./build-key client1
expect "Country Name (2 letter code) \\\\\[US]:"
send -- "US\r"
expect "State or Province Name (full name) \\\\\[CA]:"
send -- "NY\r"

expect "Locality Name (eg, city) \\\\\[SanFrancisco]:"
send -- "New York City\r"

expect "Organization Name (eg, company) \\\\\[PersonalVPNServer]:"
send -- "MyOrganization\r"

expect "Organizational Unit Name (eg, section) \\\\\[VPNUnit]:"
send -- "IT\r"

expect "Common Name (eg, your name or your server's hostname) \\\\\[client1]:"
send -- "myServer.example.com\r"

expect "Name \\\\\[server]:"
send -- "MyServer\r"

expect "Email Address \\\\\[admin@example.com]:"
send -- "myemail@example.com\r"

expect "A challenge password \\\\\[]:"
send -- "\r"

expect "An optional company name \\\\\[]:"
send -- "\r"

expect "Sign the certificate? \\\\\[y/n]:"
send -- "y\r"

expect "1 out of 1 certificate requests certified, commit? \\\\\[y/n]"
send -- "y\r"
expect eof

EOF

expect build-client-key.exp
#------------------------------------------------------------------------

#-----------------Copy generated files to openvpn folder-----------------
cd ~/openvpn-ca/keys
sudo cp ca.crt ca.key server.crt server.key ta.key dh2048.pem /etc/openvpn
#------------------------------------------------------------------------

#-----------------Configure server config--------------------------------
gunzip -c /usr/share/doc/openvpn/examples/sample-config-files/server.conf.gz | sudo tee /etc/openvpn/server.conf

sudo sed -i 's/;tls-auth ta.key 0 # This file is secret/tls-auth ta.key 0 # This file is secret\nkey-direction 0/g' /etc/openvpn/server.conf
sudo sed -i 's/;cipher AES-128-CBC   # AES/cipher AES-128-CBC   # AES\nauth SHA256/g' /etc/openvpn/server.conf
sudo sed -i 's/;user nobody/user nobody/g' /etc/openvpn/server.conf
sudo sed -i 's/;group nogroup/group nogroup/g' /etc/openvpn/server.conf
sudo sed -i 's/;push "redirect-gateway def1 bypass-dhcp"/push "redirect-gateway def1 bypass-dhcp"/g' /etc/openvpn/server.conf
sudo sed -i 's/;push "dhcp-option DNS 208.67.222.222"/push "dhcp-option DNS 208.67.222.222"/g' /etc/openvpn/server.conf
sudo sed -i 's/;push "dhcp-option DNS 208.67.220.220"/push "dhcp-option DNS 208.67.220.220"/g' /etc/openvpn/server.conf
#------------------------------------------------------------------------

#------------------Enable forwarding-------------------------------------
sudo sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/g' /etc/sysctl.conf

sudo sysctl -p
#------------------------------------------------------------------------

#------------------Add preroute rules------------------------------------
sudo sed -i 's/#   ufw-before-forward/#   ufw-before-forward\n\n\n# START OPENVPN RULES\n# NAT table rules\n*nat\n:POSTROUTING ACCEPT [0:0]\n# Allow traffic from OpenVPN client to eth0\n-A POSTROUTING -s 10.8.0.0\/8 -o eth0 -j MASQUERADE\nCOMMIT\n# END OPENVPN RULES\n/g' /etc/ufw/before.rules
#------------------------------------------------------------------------

#------------------Allow forward policy----------------------------------
sudo sed -i 's/DEFAULT_FORWARD_POLICY="DROP"/DEFAULT_FORWARD_POLICY="ACCEPT"/g' /etc/default/ufw
#------------------------------------------------------------------------

#------------------Allow ports and protocol------------------------------
sudo ufw allow 1194/udp
sudo ufw allow OpenSSH
sudo ufw disable
sudo ufw --force enable
#------------------------------------------------------------------------

#------------------Enable autostart for vpn service----------------------
sudo systemctl enable openvpn@server
sudo systemctl start openvpn@server
#------------------------------------------------------------------------

#-------------------Configure client configuration-----------------------
mkdir -p ~/client-configs/files
chmod 700 ~/client-configs/files
cp /usr/share/doc/openvpn/examples/sample-config-files/client.conf ~/client-configs/base.conf

export PUBLIC_IP=$(curl http://169.254.169.254/latest/meta-data/public-ipv4)

sudo sed -i "s/remote my-server-1 1194/remote ${PUBLIC_IP} 1194/g" ~/client-configs/base.conf
sudo sed -i 's/;user nobody/user nobody/g' ~/client-configs/base.conf
sudo sed -i 's/;group nogroup/group nogroup/g' ~/client-configs/base.conf
sudo sed -i 's/ca ca.crt/#ca ca.crt/g' ~/client-configs/base.conf
sudo sed -i 's/cert client.crt/#cert client.crt/g' ~/client-configs/base.conf
sudo sed -i 's/key client.key/#key client.key/g' ~/client-configs/base.conf
sudo sed -i 's/;cipher x/cipher AES-128-CBC\nauth SHA256\nkey-direction 1\n/g' ~/client-configs/base.conf
#------------------------------------------------------------------------

#-----------------This section needed for linux clients------------------
cat >> ~/client-configs/base.conf <<'EOF'
# script-security 2
# up /etc/openvpn/update-resolv-conf
# down /etc/openvpn/update-resolv-conf
EOF
#------------------------------------------------------------------------

#-----------------Create script for automatic generation ovpn files------
cd ~/client-configs

cat >make_config.sh <<EOF
#!/bin/bash

# First argument: Client identifier

KEY_DIR=~/openvpn-ca/keys
OUTPUT_DIR=~/client-configs/files
BASE_CONFIG=~/client-configs/base.conf

cat \${BASE_CONFIG} \\
    <(echo -e '<ca>') \\
    \${KEY_DIR}/ca.crt \\
    <(echo -e '</ca>\n<cert>') \\
    \${KEY_DIR}/\${1}.crt \\
    <(echo -e '</cert>\n<key>') \\
    \${KEY_DIR}/\${1}.key \\
    <(echo -e '</key>\n<tls-auth>') \\
    \${KEY_DIR}/ta.key \\
    <(echo -e '</tls-auth>') \\
    > \${OUTPUT_DIR}/\${1}.ovpn
EOF

chmod 700 ~/client-configs/make_config.sh

cd ~/client-configs
./make_config.sh client1
#------------------------------------------------------------------------
