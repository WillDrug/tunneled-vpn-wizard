# client-side script to deploy necessary configs. expects to auth with $KEYS/master_id.rsa
function assign_or_read {
	if [ -z ${!1+x} ]; then read -p "$1> " $1; fi;
	echo $1 is now ${!1};
}
source $1.ini;
assign_or_read "username";
assign_or_read "keypath";
assign_or_read "login";
assign_or_read "hostname";
assign_or_read "ipv4";

scp -i $keypath/master_id.rsa server_setup.sh $login@$ipv4:~/server_setup.sh
ssh -t -i $keypath/master_id.rsa $login@$ipv4 "sudo bash ~/server_setup.sh"
echo 'Waiting for the machine to reboot (presuming 30s.) TODO: automatic success detection'
read -p "press enter when machine reboots"
scp -i $keypath/master_id.rsa server_setup_two.sh $login@$ipv4:~/server_setup_two.sh
ssh -t -i $keypath/master_id.rsa $login@$ipv4 "sudo bash ~/server_setup_two.sh $username $hostname $ipv4"

mkdir $keypath/$hostname
scp -i $keypath/master_id.rsa $login@$ipv4:/home/"$username"/.ssh/"$username"_id $keypath/$hostname/"$username"_id.rsa

scp -i $keypath/master_id.rsa server_setup_ssh_reload.sh $login@$ipv4:~/server_setup_ssh_reload.sh
ssh -t -i $keypath/master_id.rsa $login@$ipv4 "sudo bash ~/server_setup_ssh_reload.sh $username $hostname $ipv4"
