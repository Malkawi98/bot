#!/bin/bash
# Script to reset the database and migrations in production

# Stop the running containers
echo "Stopping running containers..."
docker-compose -f docker-compose.prod.yml down

# Connect to the database and drop all tables
echo "Connecting to database to drop all tables..."
docker-compose -f docker-compose.prod.yml run --rm db psql -U user -d db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Start the database only
echo "Starting database..."
docker-compose -f docker-compose.prod.yml up -d db

# Wait for the database to be ready
echo "Waiting for database to be ready..."
sleep 10

# Run migrations with 'heads' instead of 'head'
echo "Running migrations with 'heads'..."
docker-compose -f docker-compose.prod.yml run --rm web sh -c "alembic -c /code/alembic.ini upgrade heads"

# Start all services
echo "Starting all services..."
docker-compose -f docker-compose.prod.yml up -d

echo "Database and migrations have been reset!"
