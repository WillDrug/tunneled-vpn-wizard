# client-side script to deploy necessary configs. expects to auth with $KEYS/master_id.rsa
function assign_or_read {
	if [ -z ${!1+x} ]; then read -p "$1> " $1; fi;
	echo $1 is now ${!1};
}
function sad {
	sed -i "s/^$1.*//" $2;
}
source $1.ini;
assign_or_read "username";
assign_or_read "keypath";
assign_or_read "login";
assign_or_read "hostname";
assign_or_read "ipv4";
assign_or_read "port";

# see if password is used for initial connection
if [ -z "${use_password+x}" ]; then 
	scp -i $keypath/master_id.rsa server_setup.sh $login@$ipv4:~/server_setup.sh
	ssh -t -i $keypath/master_id.rsa $login@$ipv4 "sudo bash ~/server_setup.sh"
else
	# password usage
	scp server_setup.sh $login@$ipv4:~/server_setup.sh
	ssh -t $login@$ipv4 "sudo bash ~/server_setup.sh"
fi;

echo 'Waiting for the machine to reboot (presuming 30s.) TODO: automatic success detection'
read -p "press enter when machine reboots"
if [ -z "${use_password+x}" ]; then 
	scp -i $keypath/master_id.rsa server_setup_two.sh $login@$ipv4:~/server_setup_two.sh
	ssh -t -i $keypath/master_id.rsa $login@$ipv4 "sudo bash ~/server_setup_two.sh $username $hostname $ipv4 $port"
else
	scp server_setup_two.sh $login@$ipv4:~/server_setup_two.sh
	ssh -t $login@$ipv4 "sudo bash ~/server_setup_two.sh $username $hostname $ipv4 $port"
fi;

mkdir $keypath/$hostname
cp $1.ini $keypath/$hostname/$hostname.ini

if [ -z "${use_password+x}" ]; then 
	scp -i $keypath/master_id.rsa $login@$ipv4:/home/"$username"/.ssh/"$username"_id $keypath/$hostname/"$username"_id.rsa
else
	scp $login@$ipv4:/home/"$username"/.ssh/"$username"_id $keypath/$hostname/"$username"_id.rsa
fi;

if [ -z "${use_password+x}" ]; then 
	scp -i $keypath/master_id.rsa server_setup_ssh_reload.sh $login@$ipv4:~/server_setup_ssh_reload.sh
	ssh -t -i $keypath/master_id.rsa $login@$ipv4 "sudo bash ~/server_setup_ssh_reload.sh $username $hostname $ipv4"
else
	scp server_setup_ssh_reload.sh $login@$ipv4:~/server_setup_ssh_reload.sh
	ssh -t $login@$ipv4 "sudo bash ~/server_setup_ssh_reload.sh $username $hostname $ipv4"
fi;

scp -P $port -i $keypath/$hostname/"$username"_id.rsa server_setup_three.sh $username@$ipv4:~/server_setup_three.sh
ssh -p $port -t -i $keypath/$hostname/"$username"_id.rsa $username@$ipv4 "sudo bash ~/server_setup_three.sh $username $hostname $ipv4"

scp -P $port -i $keypath/$hostname/"$username"_id.rsa server_setup_four.sh 
ssh -p $port -t -i $keypath/$hostname/"$username"_id.rsa $username@$ipv4 "sudo bash ~/server_setup_four.sh $username $hostname $ipv4 $port"

mkdir -p $keypath/$hostname/stunnel
mkdir -p $keypath/$hostname/openvpn
scp -P $port -i $keypath/$hostname/"$username"_id.rsa $username@$ipv4:"/home/$username/certs/{$username-*,stunnel-server.crt}" $keypath/$hostname/stunnel/
scp -P $port -i $keypath/$hostname/"$username"_id.rsa $username@$ipv4:"/home/$username/certs/{openvpn-client*,ca.crt,ta.key}" $keypath/$hostname/openvpn/

echo "[openvpn]
client = yes
accept = 127.0.0.1:1194
connect = $ipv4:443

verifyPeer = yes

CAfile = stunnel-server.crt

cert = $username-desktop.crt
key = $username-desktop.key" > $keypath/$hostname/stunnel/stunnel.conf

echo "client
dev tun
proto tcp
remote 127.0.0.1 1194
resolv-retry infinite
nobind
user nobody
group nobody
persist-key
persist-tun

ca ca.crt
cert openvpn-client.crt
key openvpn-client.key
### на клиенте 1
tls-client
tls-auth ta.key 1

remote-cert-tls server
cipher AES-256-GCM
verb 3" > $keypath/$hostname/openvpn/openvpn-client.conf

cp $keypath/$hostname/openvpn/openvpn-client.conf $keypath/$hostname/openvpn/openvpn-android-client.conf;
sad "ca" $keypath/$hostname/openvpn/openvpn-android-client.conf ;
sad "cert" $keypath/$hostname/openvpn/openvpn-android-client.conf ;
sad "key" $keypath/$hostname/openvpn/openvpn-android-client.conf;
sad "tls-auth" $keypath/$hostname/openvpn/openvpn-android-client.conf;
echo "key-direction 1" >> $keypath/$hostname/openvpn/openvpn-android-client.conf;
echo "<ca>" >> $keypath/$hostname/openvpn/openvpn-android-client.conf;
cat $keypath/$hostname/openvpn/ca.crt >> $keypath/$hostname/openvpn/openvpn-android-client.conf;
echo "</ca>"  >> $keypath/$hostname/openvpn/openvpn-android-client.conf;
echo "<cert>" >> $keypath/$hostname/openvpn/openvpn-android-client.conf;
cat $keypath/$hostname/openvpn/openvpn-client.crt >> $keypath/$hostname/openvpn/openvpn-android-client.conf;
echo "</cert>" >> $keypath/$hostname/openvpn/openvpn-android-client.conf;
echo "<key>" >> $keypath/$hostname/openvpn/openvpn-android-client.conf;
cat $keypath/$hostname/openvpn/openvpn-client.key >> $keypath/$hostname/openvpn/openvpn-android-client.conf;
echo "</key>" >> $keypath/$hostname/openvpn/openvpn-android-client.conf;
echo "<tls-auth>" >> $keypath/$hostname/openvpn/openvpn-android-client.conf;
cat $keypath/$hostname/openvpn/ta.key >> $keypath/$hostname/openvpn/openvpn-android-client.conf;
echo "</tls-auth>" >> $keypath/$hostname/openvpn/openvpn-android-client.conf;
cp $keypath/$hostname/openvpn/openvpn-client.conf $keypath/$hostname/openvpn/openvpn-client.ovpn
touch $keypath/$hostname/"$hostname".connect;
echo "ssh -i $keypath/$hostname/"$username"_id.rsa -p $port $username@$ipv4" >> $keypath/$hostname/"$hostname".connect;
echo "your connect command here is";
cat $keypath/$hostname/"$hostname".connect;