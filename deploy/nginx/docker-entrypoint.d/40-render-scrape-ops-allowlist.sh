#!/bin/sh
set -eu

output_path="/etc/nginx/snippets/scrape-ops-allowlist.conf"
allowlist="${SCRAPE_OPS_ALLOWED_CIDRS:-127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16}"

mkdir -p "$(dirname "$output_path")"
: > "$output_path"

if [ "$allowlist" = "all" ]; then
    printf 'allow all;\n' >> "$output_path"
    exit 0
fi

old_ifs=$IFS
IFS=','
set -- $allowlist
IFS=$old_ifs

for cidr in "$@"; do
    normalized_cidr="$(printf '%s' "$cidr" | tr -d '[:space:]')"
    if [ -z "$normalized_cidr" ]; then
        continue
    fi

    printf 'allow %s;\n' "$normalized_cidr" >> "$output_path"
done

printf 'deny all;\n' >> "$output_path"
