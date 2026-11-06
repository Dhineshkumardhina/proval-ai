#!/usr/bin/env bash
set -e

# Update listen_addresses in postgresql.conf
sed -i "s/^#*listen_addresses = .*/listen_addresses = '*'/" /etc/postgresql/18/main/postgresql.conf

# Add host trust rule if not already present
grep -q "host all all 0.0.0.0/0 trust" /etc/postgresql/18/main/pg_hba.conf || echo "host all all 0.0.0.0/0 trust" >> /etc/postgresql/18/main/pg_hba.conf

service postgresql restart
echo "PostgreSQL configured to listen on all interfaces!"

