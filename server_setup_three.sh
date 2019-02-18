
function uoa {
	grep -q "^$1 " $2 && sed -i "s/^$1 .*/$3/" $2 || printf "\n$3" >> $2
}

# now for openvpn
echo "> Installing OpenVPN and RSA"
cd /opt/ && sudo curl -O -L https://github.com/OpenVPN/easy-rsa/archive/master.zip
sudo unzip master.zip && rm -f master.zip
cd easy-rsa-master/easyrsa3/ && cp vars.example vars
echo "> Configuring EasyRSA"
uoa "set_var EASYRSA_DN" /opt/easy-rsa-master/easyrsa3/vars 'set_var EASYRSA_DN "cn_only"';
uoa "set_var EASYRSA_ALGO" /opt/easy-rsa-master/easyrsa3/vars "set_var EASYRSA_ALGO            ec";
uoa "set_var EASYRSA_CURVE" /opt/easy-rsa-master/easyrsa3/vars "set_var EASYRSA_CURVE           secp521r1";
uoa "set_var EASYRSA_CA_EXPIRE" /opt/easy-rsa-master/easyrsa3/vars "set_var EASYRSA_CA_EXPIRE       3650";
uoa "set_var EASYRSA_CERT_EXPIRE" /opt/easy-rsa-master/easyrsa3/vars "set_var EASYRSA_CERT_EXPIRE     3650";
uoa "set_var EASYRSA_CRL_DAYS" /opt/easy-rsa-master/easyrsa3/vars "set_var EASYRSA_CRL_DAYS        3650";
export EASYRSA_VARS_FILE=/opt/easy-rsa-master/easyrsa3/vars
echo "> Generating certificates"
./easyrsa init-pki
./easyrsa --batch build-ca nopass
./easyrsa build-server-full openvpn-server nopass
./easyrsa build-client-full openvpn-client nopass

cp -p pki/ca.crt pki/private/openvpn-server.key pki/issued/openvpn-server.crt /etc/openvpn/server/
mkdir -p /home/$1/certs
cp -p pki/ca.crt pki/private/openvpn-client.key pki/issued/openvpn-client.crt /home/$1/certs/

echo "> Configuring openvpn server"
cd /etc/openvpn/server/
openvpn --genkey --secret ta.key
cp -p ta.key /home/$1/certs/
echo "> Using 208.67.222.222 and 208.67.220.220 DNS, change in /etc/openvpn/server/openvpn-server.conf if needed"
echo 'local 127.0.0.1
port 1194
### Stunnel TCP only
proto tcp
### Tunnel mode
dev tun

### Certificate and key files
ca ca.crt
cert openvpn-server.crt
key openvpn-server.key
### Turning on Elliptic Curve Diffie נHellman (ECDH)
dh none
### Server-side 0
tls-server
tls-auth ta.key 0
### Control channel cipher
tls-cipher TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384:TLS-ECDHE-ECDSA-WITH-CHACHA20-POLY1305-SHA256
### Data channel cipher
cipher AES-256-GCM

server 10.8.8.0 255.255.255.0
### Tunnel all traffic
push "redirect-gateway def1"
push "route ' $3 ' 255.255.255.255 net_gateway"
push "dhcp-option DNS 208.67.222.222"
push "dhcp-option DNS 208.67.220.220"

### Multiple client certificate
duplicate-cn
keepalive 10 120

user nobody
group nobody
persist-key
persist-tun

### Disable logs to preserver space
status /dev/null
log /dev/null
verb 0' > /etc/openvpn/server/openvpn-server.conf
echo "> Starting OpenVPN"
systemctl start openvpn-server@openvpn-server
if $(/usr/bin/systemctl -q is-active openvpn-server@openvpn-server) ; then 
	echo "> OpenVPN is configured ok";
else 
	echo "> OpenVPN failed! ";
	exit
fi
systemctl enable openvpn-server@openvpn-server
echo "> Installign stunnel"
cd /opt && curl -O -L https://rpmfind.net/linux/fedora/linux/updates/25/x86_64/Packages/s/stunnel-5.41-1.fc25.x86_64.rpm
rpm -ivh stunnel-5.41-1.fc25.x86_64.rpm
rpm -qi stunnel

useradd -d /var/stunnel -m -s /bin/false stunnel
ls -ld /var/stunnel
echo '### Remember! Exec is from chroot!
chroot = /var/stunnel
setuid = stunnel
setgid = stunnel
pid = /stunnel.pid

debug = 0

## performance tunning
socket = l:TCP_NODELAY=1
socket = r:TCP_NODELAY=1

### curve used for ECDHE
curve = secp521r1
sslVersion = all
options = NO_SSLv2
options = NO_SSLv3

[openvpn]
accept = 443
connect = 127.0.0.1:1194
renegotiation = no

### RSA
ciphers = ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-RSA-AES256-SHA
cert = /etc/stunnel/stunnel-server.crt
key = /etc/stunnel/stunnel-server.key
CAfile = /etc/stunnel/clients.crt
verifyPeer = yes' > /etc/stunnel/stunnel.conf
cd /etc/stunnel
echo "> Generating stunnel keys"
openssl req -newkey rsa:2048 -nodes -keyout stunnel-server.key -x509 -days 3650 -subj "/CN=stunnel-server" -out stunnel-server.crt
openssl req -newkey rsa:2048 -nodes -keyout $1-desktop.key -x509 -days 3650 -subj "/CN=$1-desktop" -out $1-desktop.crt
openssl req -newkey rsa:2048 -nodes -keyout $1-mobile.key -x509 -days 3650 -subj "/CN=$1-mobile" -out $1-mobile.crt
openssl pkcs12 -export -in $1-mobile.crt -inkey $1-mobile.key -out $1-mobile.p12

cat $1-desktop.crt > clients.crt
cat $1-mobile.crt >> clients.crt
echo "> Starting stunnel"
systemctl start stunnel
if $(/usr/bin/systemctl -q is-active stunnel) ; then 
	echo "> Stunnel is configured ok";
else 
	echo "> Stunnel failed! ";
	exit
fi
systemctl enable stunnel
cp -p $1-* stunnel-server.crt /home/$1/certs/
