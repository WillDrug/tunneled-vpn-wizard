yum clean all;
yum check;
yum check-update;
yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm;
yum update -y;
# presuming selinux config present
grep -q SELINUX= /etc/selinux/config && sed -i 's/SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config || printf "\nSELINUX=permissive" >> /etc/selinux/config;
# now to restart
sudo reboot;