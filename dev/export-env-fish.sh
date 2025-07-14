# Export environment variables from the .env file in the first argument.
# If no argument is given, default to "dev/.env.docker-compose-native".
# This file must be sourced, not run.

if [ -z $FISH_VERSION ]; then
  echo "Fish shell not found"
  exit 1
end

if [ -n "$1" ]; then
  # If an argument was provided, use it as the .env file
  set _dotenv_file $1
else
  set _dotenv_dir (dirname (status --current-filename))
  set _dotenv_file $_dotenv_dir/.env.docker-compose-native
end

echo "Sourcing $_dotenv_file..."
echo

# Go through each line in the .env file and extract the value
for line in (cat $_dotenv_file | grep -v '^#' | grep -v '^\s*$')
  set item (string split -m 1 '=' $line)

  # Strip leading/trailing double quotes from value
  set item[2] (echo $item[2] | sed -e 's/^"//' -e 's/"$//')

  # Pass value through bash, to ensure variable interpolation
  set item[2] (bash -c "echo $item[2]")

  set -gx $item[1] $item[2]
  echo "Exported key $item[1]"
end

set -e _dotenv_dir
set -e _dotenv_file
