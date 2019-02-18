function uoa {
	grep -q "^$1 " $2 && sed -i "s/^$1 .*/$3/" $2 || printf "\n$3" >> $2
}

systemctl enable iptables
echo "> Checking firewalld"
if $(/usr/bin/systemctl -q is-active firewalld) ; then 
	echo "> Firewalld running, stopping";
	systemctl stop firewalld;
	systemctl disable firewalld;
	systemctl status firewalld;
fi
echo "> Dropping iptables"
iptables -P INPUT ACCEPT;
iptables -P FORWARD ACCEPT;
iptables -P OUTPUT ACCEPT;
iptables -t nat -F;
iptables -t mangle -F;
iptables -F;
iptables -X;
ip6tables -P INPUT ACCEPT;
ip6tables -P FORWARD ACCEPT;
ip6tables -P OUTPUT ACCEPT;
ip6tables -t nat -F;
ip6tables -t mangle -F;
ip6tables -F;
ip6tables -X;
echo "> Configuring iptables"
iptables -A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT;
iptables -A INPUT -i lo -j ACCEPT;
iptables -A INPUT -p icmp --icmp-type 8 -j ACCEPT;
iptables -A INPUT -p tcp --dport 443 -j ACCEPT;
iptables -A INPUT -p tcp --dport 31337 -j ACCEPT;
iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT;
iptables -A FORWARD -i tun+ -s 10.8.8.0/24 -j ACCEPT;
iptables -t nat -A POSTROUTING -s 10.8.8.0/24 -o eth0 -j SNAT --to-source  $(echo $(ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1) | cut -d ' ' -f 1);
iptables -P INPUT DROP;
iptables -P FORWARD DROP;
iptables-save > /etc/sysconfig/iptables;
systemctl enable iptables;
uoa "net.ipv4.ip_forward" /etc/sysctl.conf "net.ipv4.ip_forward = 1"
sysctl net.ipv4.ip_forward=1
chown $1: /home/$1/certs/{ta.key,ca.crt,openvpn-client.crt,openvpn-client.key,$1-*}
