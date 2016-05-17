#!/bin/bash

echo "[1] Generate key for users"
echo "[2] Generate key for robots"

read -p "Key type: " userinput
read -p "Key file name: " fname


if [ $userinput -eq 1 ] ; then folder="userside"
elif [ $userinput -eq 2 ] ; then folder="robotside"
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
rm ./easy-rsa/$folder/keys/$fname.csr
