# Use the official PostgreSQL image as a parent image
FROM postgres:16.1

# Set environment variables for PostgreSQL
ENV POSTGRES_DB=social
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=password

# Copy the SQL initialization script into the container
COPY init-db.sql /docker-entrypoint-initdb.d/

# Expose PostgreSQL port
EXPOSE 5432

# Default command to run PostgreSQL
CMD ["postgres"]