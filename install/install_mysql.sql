CREATE USER 'piccolo'@'localhost' IDENTIFIED BY '$MYSQL_PASSWORD';
GRANT ALL PRIVILEGES ON *.* TO 'piccolo'@'localhost' WITH GRANT OPTION;