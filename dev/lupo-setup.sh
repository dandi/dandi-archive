#!/usr/bin/env bash
# Bring up a local lupo (DataCite REST API) from dev/docker-compose.lupo.yml
# and run its one-time setup, so the test suite can mint DOIs against it.
#
# After this, point the archive at it with:
#   DJANGO_DANDI_DOI_API_URL=http://localhost:8065/dois
#   DJANGO_DANDI_DOI_API_USER=DATACITE.TESTUSER
#   DJANGO_DANDI_DOI_API_PASSWORD=test_mds_password
#   DJANGO_DANDI_DOI_API_PREFIX=10.14454
#
# Tear down with: docker compose -f dev/docker-compose.lupo.yml down -v
set -eu

compose_file="$(dirname "$0")/docker-compose.lupo.yml"
compose=(docker compose -f "$compose_file")

# Safety first: refuse to run if the environment already points the archive at a DataCite
# server other than this local one: the suite could produce real undeletable DOIs there.
url="${DJANGO_DANDI_DOI_API_URL:-}"
case "$url" in
  '' | http://localhost:* | http://127.0.0.1:*) ;;
  *)
    echo "DJANGO_DANDI_DOI_API_URL is set to '$url', not a local lupo; refusing." >&2
    exit 1
    ;;
esac

"${compose[@]}" up -d --wait

# Search indices must exist before the seed writes, or lupo auto-creates
# unmapped ones and every list endpoint returns 400.
"${compose[@]}" exec -T web bundle exec rake elasticsearch:create_all_indexes
# Create the database and load the schema, then seed the DATACITE.TESTUSER
# client. The seed is a plain Ruby file under db/seeds/development/, refused
# only in production; the seedbank tasks that normally run it are a
# development-group gem, absent in the test environment, so load it directly.
"${compose[@]}" exec -T web bundle exec rake db:create db:schema:load
"${compose[@]}" exec -T web bundle exec rails runner db/seeds/development/base.seeds.rb

# Sanity check: an authenticated list succeeds only if the app is serving, the
# seeded client's credentials validate, and the search indices have mappings.
curl -fsS -u DATACITE.TESTUSER:test_mds_password http://localhost:8065/dois >/dev/null
echo "lupo is up at http://localhost:8065"
