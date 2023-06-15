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

iptables -A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT;
iptables -A INPUT -i lo -j ACCEPT;
iptables -A INPUT -p icmp --icmp-type 8 -j ACCEPT;
iptables -A INPUT -p tcp --dport 443 -j ACCEPT;
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -i tun+ -j ACCEPT
iptables -A FORWARD -i tun+ -j ACCEPT
iptables -A FORWARD -i tun+ -o $(ip -br l | awk '"'"'$1 !~ "lo|vir|wl" { print $1; getline }'"'"') -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i $(ip -br l | awk '"'"'$1 !~ "lo|vir|wl" { print $1; getline }'"'"') -o tun+ -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -t nat -A POSTROUTING -s 10.8.8.0/24 -o $(ip -br l | awk '"'"'$1 !~ "lo|vir|wl" { print $1; getline }'"'"') -j SNAT --to-source  $(echo $(ip addr show $(ip -br l | awk '"'"'$1 !~ "lo|vir|wl" { print $1; getline }'"'"') | grep "inet\b" | awk '"'"'{print $2}'"'"' | cut -d/ -f1) | cut -d '"'"' '"'"' -f 1);
iptables -A OUTPUT -o $(ip -br l | awk '"'"'$1 !~ "lo|vir|wl" { print $1; getline }'"'"') -j ACCEPT
iptables -A OUTPUT -o tun+ -j ACCEPT
iptables -A OUTPUT -p tcp --sport 22 -m state --state ESTABLISHED -j ACCEPT
iptables -A OUTPUT -m state --state NEW,ESTABLISHED,RELATED -p tcp -m multiport --dports 80,443 -j ACCEPT
iptables -A OUTPUT -p icmp --icmp-type echo-request -j ACCEPT
iptables -A OUTPUT -p udp --sport 53 -j ACCEPT
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

iptables -P INPUT DROP;
iptables -P FORWARD DROP;
iptables -P OUTPUT DROP;