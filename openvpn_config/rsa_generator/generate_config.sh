#!/bin/bash

echo "[1] Generate config for users"
echo "[2] Generate config for robots"

read -p ">" userinput
read -p "Client name:" fname


if [ $userinput -eq 1 ] ; then folder="userside"; conf="userclient.conf"
elif [ $userinput -eq 2 ] ; then folder="robotside"; conf="robotclient.conf"
else
echo "Incorrect value"
exit -1
fi

CWD=$(pwd)

cd ./easy-rsa/$folder/
source ./vars
./build-key $fname
cd $CWD
mv ./easy-rsa/$folder/keys/$fname.crt ./easy-rsa/$folder/keys/$fname.key ./keys/$folder/
cp ./easy-rsa/$folder/keys/ca.crt ./keys/$folder/
rm ./easy-rsa/$folder/keys/$fname.csr
cp ./easy-rsa/$conf ./keys/$folder/

mv ./keys/$folder/$fname.crt ./keys/$folder/client.crt
mv ./keys/$folder/$fname.key ./keys/$folder/client.key

cd ./keys/$folder/
tar -cf $fname.tar client.key client.crt ca.crt $conf
rm client.key client.crt ca.crt $conf
cd $CWD
