
function uoa {
	grep -q "^$1 " $2 && sed -i "s/^$1 .*/$3/" $2 || printf "\n$3" >> $2
}

# installing vpn
echo "> Installing software"
yum install -y iptables-services openvpn unzip
# adding a new user
echo "> Adding user $1"
useradd -G wheel -m $1
passwd $1
# UNCOMMENT to set a password. Really should use keys
#passwd $1
# checking that wheel is in sudoers or adding
echo "> Checking wheel privileges"
grep -q "%wheel\sALL=(ALL)\sALL" /etc/sudoers || echo "%wheel ALL=(ALL) ALL" >> /etc/sudoers

# no password auth, no root login, NO ACCESS FUCK YOU
echo "> Configuring ssh"
cp -f /etc/ssh/sshd_config /etc/ssh/sshd_config.old
uoa Port /etc/ssh/sshd_config "Port 31337"
uoa PasswordAuthentication /etc/ssh/sshd_config "PasswordAuthentication no"
uoa PermitRootLogin /etc/ssh/sshd_config "PermitRootLogin no"
uoa PubkeyAuthentication /etc/ssh/sshd_config "PubkeyAuthentication yes"
#grep -q "^Port " /etc/ssh/sshd_config && sed -i 's/^Port .*/Port 31337/' /etc/ssh/sshd_config || printf "\nPort 31337" >> /etc/ssh/sshd_config
#grep -q "^PasswordAuthentication " /etc/ssh/sshd_config && sed -i 's/^PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config || printf "\nPasswordAuthentication no" >> /etc/ssh/sshd_config
#grep -q "^PermitRootLogin " /etc/ssh/sshd_config && sed -i 's/^PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config || printf "\nPermitRootLogin no" >> /etc/ssh/sshd_config

# TODO: check why this doesn't actually work
mkdir -p /home/$1/.ssh
chmod 700 /home/$1/.ssh
touch /home/$1/.ssh/authorized_keys
chmod 600 /home/$1/.ssh/authorized_keys
ssh-keygen -t rsa -f /home/$1/.ssh/$1_id
chown -R $1:$1 /home/$1/.ssh
cat /home/$1/.ssh/$1_id.pub >> /home/$1/.ssh/authorized_keys
