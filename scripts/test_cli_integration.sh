#!/bin/bash
# Build local dandi-archive Docker image and run CLI integration tests against it
# This emulates the CI workflow but uses your local code changes

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
CLI_PATH="../dandi-cli"
BUILD_IMAGE=true
CLEANUP=true
TEST_PATTERN=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --cli-path)
            CLI_PATH="$2"
            shift 2
            ;;
        --test)
            TEST_PATTERN="$2"
            shift 2
            ;;
        --no-build)
            BUILD_IMAGE=false
            shift
            ;;
        --no-cleanup)
            CLEANUP=false
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --cli-path PATH  Path to dandi-cli repository (default: ../dandi-cli)"
            echo "  --test PATTERN   Specific test pattern relative to dandi package (e.g. tests/test_dandiapi.py::test_name)"
            echo "  --no-build       Skip building Docker image (use existing)"
            echo "  --no-cleanup     Don't stop Docker containers after tests (useful for debugging)"
            echo "  --help           Show this help message"
            echo ""
            echo "This script:"
            echo "1. Builds dandiarchive-api Docker image from local dandi-archive code"
            echo "2. Installs dandi-cli from local repository path"
            echo "3. Runs CLI integration tests against the Docker image"
            echo "4. Optionally cleans up containers"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Test with default ../dandi-cli"
            echo "  $0 --cli-path /path/to/dandi-cli     # Test with custom CLI path"
            echo "  $0 --test tests/test_dandiapi.py     # Run specific test"
            echo "  $0 --no-cleanup                      # Debug mode (keep containers)"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if we're in the right directory
if [[ ! -f "manage.py" ]]; then
    print_error "This script must be run from the dandi-archive directory (where manage.py is located)"
    exit 1
fi

# Validate CLI path
if [[ ! -d "$CLI_PATH" ]]; then
    print_error "CLI path '$CLI_PATH' does not exist. Check your --cli-path setting."
    exit 1
fi

# Clean up any existing containers first
print_status "Cleaning up any existing Docker containers..."
DOCKER_COMPOSE_FILE="$CLI_PATH/dandi/tests/data/dandiarchive-docker/docker-compose.yml"
if [[ -f "$DOCKER_COMPOSE_FILE" ]]; then
    print_status "Stopping and removing existing containers..."
    docker compose -f "$DOCKER_COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true

    # Also clean up any containers that might be using the conflicting ports
    print_status "Checking for containers using ports 8000, 9000, 5432..."
    for port in 8000 9000 5432; do
        container_id=$(docker ps -q --filter "publish=$port" 2>/dev/null || true)
        if [[ -n "$container_id" ]]; then
            print_warning "Found container $container_id using port $port, stopping it..."
            docker stop "$container_id" 2>/dev/null || true
            docker rm "$container_id" 2>/dev/null || true
        fi
    done

    # Wait a moment for cleanup to complete
    sleep 3
fi

# Build Docker image if requested
if [[ "$BUILD_IMAGE" == true ]]; then
    print_status "Building dandiarchive-api Docker image from local code..."
    docker build \
        -t dandiarchive/dandiarchive-api \
        -f dev/django-public.Dockerfile \
        .

    print_status "Docker image built successfully"
else
    print_status "Skipping Docker build (using existing dandiarchive/dandiarchive-api image)"
fi

# Install dandi-cli
print_status "Installing development version of dandi-cli from $CLI_PATH..."
pip install -e "$CLI_PATH[test]"

print_status "Setting up environment for CLI tests..."
export DANDI_ALLOW_LOCALHOST_URLS=1
export DANDI_TESTS_PULL_DOCKER_COMPOSE=0

if [[ "$CLEANUP" == false ]]; then
    print_status "Setting up debug mode (containers will not be cleaned up)"
    # Persist containers to prevent cleanup
    export DANDI_TESTS_PERSIST_DOCKER_COMPOSE=1
else
    unset DANDI_TESTS_PERSIST_DOCKER_COMPOSE
fi

# Find dandi package location - use CLI repo path since we're always using dev version
DANDI_PACKAGE_PATH="$CLI_PATH/dandi"

print_status "Starting Docker containers..."
docker compose -f "$DOCKER_COMPOSE_FILE" up -d

print_status "Running CLI integration tests..."

# Set up test path (use installed package location)
if [[ -n "$TEST_PATTERN" ]]; then
    # TEST_PATTERN should be relative to the dandi package (e.g. tests/test_dandiapi.py::test_name)
    TEST_PATH="$DANDI_PACKAGE_PATH/$TEST_PATTERN"
    print_status "Running specific test pattern: $TEST_PATTERN"

    # Check if test file exists (strip :: and test names for file check)
    TEST_FILE_PATH="${TEST_PATH%%::*}"
    if [[ ! -e "$TEST_FILE_PATH" ]]; then
        print_error "Test file does not exist: $TEST_FILE_PATH"
        exit 1
    fi
else
    TEST_PATH="$DANDI_PACKAGE_PATH/tests/"
    print_status "Running all --dandi-api tests..."
fi

# Change to the CLI directory so pytest finds the right conftest.py
cd "$CLI_PATH"
echo "PWD"
pwd
python -m pytest --dandi-api -v "$TEST_PATH" --tb=short

print_status "Tests completed!"

# Show docker compose info
print_status "Docker compose file: $DOCKER_COMPOSE_FILE"

if [[ "$CLEANUP" == true ]]; then
    print_status "Cleaning up Docker containers..."
    docker compose -f "$DOCKER_COMPOSE_FILE" down -v
    print_status "Cleanup complete"
else
    print_status "Containers left running for debugging. You can:"
    print_status "  Access Django shell: docker compose -f \"$DOCKER_COMPOSE_FILE\" exec django python manage.py shell_plus"
    print_status "  View logs: docker compose -f \"$DOCKER_COMPOSE_FILE\" logs --timestamps"
    print_status "  Clean up manually: docker compose -f \"$DOCKER_COMPOSE_FILE\" down -v"
fi
print_status "Done!"
