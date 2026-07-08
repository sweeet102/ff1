#!/bin/bash
# Wrapper: compile P4 via amd64 Docker image (no bind-mount to avoid Rosetta bug)
set -e

ARGS=("$@")
OUTFILE=""
INFILE=""
P4V=""
P4RT=""

i=0
while [ $i -lt $# ]; do
    case "${ARGS[$i]}" in
        -o) OUTFILE="${ARGS[$((i+1))]}"; i=$((i+1)) ;;
        --p4v) P4V="${ARGS[$((i+1))]}"; i=$((i+1)) ;;
        --p4runtime-files) P4RT="${ARGS[$((i+1))]}"; i=$((i+1)) ;;
        *.p4) INFILE="${ARGS[$i]}" ;;
    esac
    i=$((i+1))
done

if [ -z "$INFILE" ]; then
    echo "Error: no .p4 input file found"
    exit 1
fi

INBASE=$(basename "$INFILE")
OUTBASE=$(basename "${OUTFILE:-output.json}")
P4RTBASE=$(basename "${P4RT:-output.txtpb}")

DOCKER_ARGS="--p4v ${P4V:-16} -o /tmp/$OUTBASE"
[ -n "$P4RT" ] && DOCKER_ARGS="$DOCKER_ARGS --p4runtime-files /tmp/$P4RTBASE"

CID=$(docker create --platform linux/amd64 p4lang/p4c:latest \
    p4c-bm2-ss $DOCKER_ARGS /tmp/"$INBASE")

docker cp "$INFILE" "$CID:/tmp/$INBASE"
docker start -a "$CID" 2>&1 | grep -v "EventletDeprecationWarning\|not greened\|RLock" || true

# Copy output back
[ -n "$OUTFILE" ] && mkdir -p "$(dirname "$OUTFILE")" && docker cp "$CID:/tmp/$OUTBASE" "$OUTFILE" 2>/dev/null || true
[ -n "$P4RT" ] && mkdir -p "$(dirname "$P4RT")" && docker cp "$CID:/tmp/$P4RTBASE" "$P4RT" 2>/dev/null || true

docker rm "$CID" >/dev/null 2>&1 || true
