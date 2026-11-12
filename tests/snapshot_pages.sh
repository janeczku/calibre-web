#!/usr/bin/env bash
# Save the HTML of a fixed set of pages, for before/after diffs of template changes.
# Usage: CW_USER=admin CW_PASS=secret tests/snapshot_pages.sh http://127.0.0.1:8083 /tmp/snap/before
set -u
BASE="${1:?base url}"
OUT="${2:?output dir}"
mkdir -p "$OUT"
JAR="$(mktemp)"
trap 'rm -f "$JAR"' EXIT
status=0

fetch() {  # fetch <path> <slug> <expected status>
    local code
    code=$(curl -s -b "$JAR" -c "$JAR" -o "$OUT/$2.html" -w "%{http_code}" "$BASE$1")
    if [ "$code" != "$3" ]; then
        echo "FAIL $1 -> $code (expected $3)" >&2
        status=1
    fi
}

csrf=$(curl -s -c "$JAR" "$BASE/login" | sed -n 's/.*name="csrf_token" value="\([^"]*\)".*/\1/p' | head -1)
curl -s -b "$JAR" -c "$JAR" -o /dev/null --data-urlencode "csrf_token=$csrf" \
    --data-urlencode "username=$CW_USER" --data-urlencode "password=$CW_PASS" "$BASE/login"

fetch / index 200
book=$(grep -o 'href="/book/[0-9]*"' "$OUT/index.html" | head -1 | sed 's/href="\(.*\)"/\1/')
[ -n "$book" ] && fetch "$book" book 200 || { echo "FAIL no book link on index" >&2; status=1; }
fetch "/search/stored?query=a" search 200
fetch /advsearch advsearch 200
fetch /me me 200
fetch /stats stats 200
fetch /tasks tasks 200
fetch /admin/view admin 200
fetch /admin/config config 200
fetch /admin/viewconfig viewconfig 200
fetch /admin/mailsettings mailsettings 200
fetch /admin/usertable usertable 200
fetch /admin/scheduledtasks scheduledtasks 200
fetch /admin/user/1 user1 200
fetch /simpleshelf/1 simpleshelf 200
fetch /shelf/1 shelf 200
fetch /does-not-exist notfound 404
curl -s -b "$JAR" -c "$JAR" -o /dev/null "$BASE/logout"
fetch /login login 200
exit $status
