#!/bin/bash
# Mac-side P4 compiler: compiles .p4 in Docker, outputs to exercises build dir
# Usage: p4c-wrapper.sh <exercise_dir>

EXERCISE_DIR="$1"
EXERCISE=$(basename "$EXERCISE_DIR")
EXERCISES_ROOT="/Users/wenzhiyuan/Desktop/ff1/p4-lab/p4-tutorials/exercises"
P4_FILE="$EXERCISES_ROOT/$EXERCISE/$EXERCISE.p4"
BUILD_DIR="$EXERCISES_ROOT/$EXERCISE/build"

mkdir -p "$BUILD_DIR"

echo "Compiling $EXERCISE.p4 ..."
docker run --rm --platform linux/amd64 \
    -v "$EXERCISES_ROOT/$EXERCISE:/work:ro" \
    -v "$BUILD_DIR:/output" \
    p4lang/p4c:latest \
    p4c-bm2-ss --p4v 16 --p4runtime-files "/output/$EXERCISE.p4.p4info.txtpb" -o "/output/$EXERCISE.json" "/work/$EXERCISE.p4" 2>&1

ls -la "$BUILD_DIR/$EXERCISE.json" 2>/dev/null && echo "OK" || echo "FAILED"
