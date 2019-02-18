
rm /home/$1/.ssh/$1_id
systemctl reload sshd
if $(/usr/bin/systemctl -q is-active sshd.service) ; then 
	echo "> SSH is configured ok";
	rm -f /etc/ssh/sshd_config.old;
else 
	echo "> SSH IS NOT OK! DROPPING CONFIG AND PANICKING";
	mv -f sshd_config.old sshd_config;
	exit
fi

