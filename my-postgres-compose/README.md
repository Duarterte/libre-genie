# PostgreSQL Docker Compose Setup

This project provides a Docker Compose configuration for setting up a PostgreSQL database using Docker. It includes all necessary files to build the PostgreSQL image, initialize the database, and manage environment variables.

## Project Structure

```
my-postgres-compose
├── db
│   ├── Dockerfile
│   └── initdb
│       └── init.sql
├── docker-compose.yml
├── .env
└── README.md
```

## Files Overview

- **db/Dockerfile**: Contains instructions to build a Docker image for PostgreSQL, including the base image and configurations.
  
- **db/initdb/init.sql**: SQL script that initializes the database with necessary tables and data when the PostgreSQL container starts.

- **docker-compose.yml**: Defines the services, networks, and volumes for the Docker application. It specifies the PostgreSQL service, including build context, image, environment variables from the `.env` file, and necessary ports.

- **.env**: Contains environment variables used by the Docker Compose configuration, such as database credentials and configuration settings.

## Setup Instructions

1. **Clone the Repository**: Clone this repository to your local machine.

2. **Navigate to the Project Directory**: Change into the project directory:
   ```
   cd my-postgres-compose
   ```

3. **Configure Environment Variables**: Update the `.env` file with your database credentials and settings.

4. **Build and Start the Containers**: Run the following command to build the Docker image and start the PostgreSQL service:
   ```
   docker-compose up --build
   ```

5. **Access the Database**: You can connect to the PostgreSQL database using any PostgreSQL client with the credentials specified in the `.env` file.

## Usage

- To stop the containers, run:
  ```
  docker-compose down
  ```

- To view logs, use:
  ```
  docker-compose logs
  ```

## Additional Information

For more details on Docker and PostgreSQL, refer to the official documentation for [Docker](https://docs.docker.com/) and [PostgreSQL](https://www.postgresql.org/docs/).