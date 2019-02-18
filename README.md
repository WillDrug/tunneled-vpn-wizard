# OpenVPN+Stunnel server configurator
Pull requests are welcome

# How to use?
Script only works on CentOS machines right now!!
1) Create an .ini file with server parameters, including
* `username`: new user to be created
* `keypath`: path on client machine to find master_id.rsa and to store newely created id's
* `login`: server login (usually root right away)
* `hostname`: used to create directories and store certificates in `keypath`
* `ipv4`: ipv4 address of the server

2) Run script with $1 = .ini file
Script expects master_id.rsa to be in `$keypath` directory (!!)

3) MAGIC!

(You can run ssh_only.sh to just reconfigure SSH to be `cool` and download new keys)


# WARNING
The script will
1) Disallow password authentication
2) Change ssh port to `31337` because I'm cool
3) Update yum
4) Install openvpn and stunnel
5) Create certificates for them and keys for ssh
6) Configure openvpn+stunnel+ssh
7) Download certificates and keys
8) Configure IPTables

Do not use on servers you're not ready to loose. Script's tested on new DigitalOcean droplets.


# Additional
If you still want to use the weird $keypath things, you can connect to your servers using this script:
```source $KEYS/$1/$1.ini
if [ -z "$port"  ]
then
    echo "Setting port to default";
    port=31337;
fi;
ssh -p $port -i $KEYS/$hostname/"$username"_id.rsa $username@$ipv4
```