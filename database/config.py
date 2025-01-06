import os


username = open("secrets/mysql/user.txt").read()
password = open("secrets/mysql/password.txt").read()
database = open("secrets/mysql/database.txt").read()

host = os.getenv("MYSQL_HOST", "0.0.0.0")

driver = "mysql+mysqldb"
sqlalchemy_url = f"{driver}://{username}:{password}@{host}/{database}"

# root_password = open("secrets/mysql/root_password.txt").read()
