
username = open("secrets/mysql/user.txt").read()
password = open("secrets/mysql/password.txt").read()
database = open("secrets/mysql/database.txt").read()
host = "0.0.0.0"

driver = "mysql+mysqldb"
sqlalchemy_url = f"{driver}://{username}:{password}@0.0.0.0/{database}"

# root_password = open("secrets/mysql/root_password.txt").read()
