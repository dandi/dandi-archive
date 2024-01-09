#!/bin/bash

# This script can be used to launch the linc-archive UI with ease locally
# Happy developing!

if [ $# -lt 2 ]; then
  echo "Usage: $0 <image_name> <your.email@email.com>"
  exit 1
fi

image_name=$1
email=$2

cd web/

# Build Docker image (include the path to the Dockerfile's context)
docker build -t $image_name -f Dockerfile.dev .

# Run the Docker container for frontend in background
docker run -d -v "$(pwd):/usr/src/app" -v /usr/src/app/node_modules -p 8085:8085 -e CHOKIDAR_USEPOLLING=true $image_name

cd ..

# Run Docker Compose commands for backend
docker-compose run --rm django ./manage.py migrate
docker-compose run --rm django ./manage.py createcachetable
docker-compose run --rm django ./manage.py createsuperuser
docker-compose run --rm django ./manage.py create_dev_dandiset --owner $email

# Run Application
docker-compose up
