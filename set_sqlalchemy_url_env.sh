#! /bin/bash

DRIVER="mysql+mysqldb"
DBUSER=$(cat secrets/mysql/user.txt | head -n1)
PASSWORD=$(cat secrets/mysql/password.txt | head -n1)
DBNAME=$(cat secrets/mysql/database.txt | head -n1)
export SQLALCHEMY_URL="${DRIVER}://${DBUSER}:${PASSWORD}@0.0.0.0/${DBNAME}"