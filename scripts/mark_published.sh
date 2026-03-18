#!/bin/bash
# Создать .published во всех папках материалов типа ПШ (уже загружены в БЗ)
set -euo pipefail

ARCHIVE_DIR="${1:-/mnt/main/work/bz2/video/archive}"

if [ ! -d "$ARCHIVE_DIR" ]; then
    echo "ERROR: Archive directory not found: $ARCHIVE_DIR"
    exit 1
fi

count=0
for year_dir in "$ARCHIVE_DIR"/*/; do
    psh_dir="${year_dir}ПШ"
    if [ -d "$psh_dir" ]; then
        for topic_dir in "$psh_dir"/*/; do
            if [ -d "$topic_dir" ]; then
                touch "${topic_dir}.published"
                echo "  ${topic_dir}"
                count=$((count + 1))
            fi
        done
    fi
done

echo ""
echo "Done: marked $count materials as published"
