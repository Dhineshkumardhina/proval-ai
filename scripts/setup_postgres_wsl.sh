#!/usr/bin/env bash
set -e

# Start postgres service
service postgresql start

# Create user propval_user and database propval_test with superuser or rls privileges
su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='propval_user'\" | grep -q 1 || psql -c \"CREATE USER propval_user WITH PASSWORD 'propval_password' SUPERUSER;\""
su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='propval_test'\" | grep -q 1 || psql -c \"CREATE DATABASE propval_test OWNER propval_user;\""

# Ensure pg_hba.conf allows local password connection
sed -i 's/local   all             all                                     peer/local   all             all                                     trust/' /etc/postgresql/18/main/pg_hba.conf
sed -i 's/host    all             all             127.0.0.1\/32            scram-sha-256/host    all             all             127.0.0.1\/32            trust/' /etc/postgresql/18/main/pg_hba.conf
sed -i 's/host    all             all             ::1\/128                 scram-sha-256/host    all             all             ::1\/128                 trust/' /etc/postgresql/18/main/pg_hba.conf

service postgresql reload

su - postgres -c "psql -d propval_test -c 'SELECT version();'"
echo "PostgreSQL setup complete!"

