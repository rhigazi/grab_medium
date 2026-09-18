#!/usr/bin/env bash
set -euo pipefail

# Usage: bash_scanner.sh <TARGET_DIR> <MEDIA_ID>

TARGET_DIR="${1:-.}"
MEDIA_ID="${2:-1}"

# Resolve target directory absolute path
if [[ "$OSTYPE" == "darwin"* ]]; then
    TARGET_DIR=$(cd "$TARGET_DIR" && pwd -P)
else
    TARGET_DIR=$(readlink -f "$TARGET_DIR" 2>/dev/null || (cd "$TARGET_DIR" && pwd -P))
fi

# Ensure no trailing slash on TARGET_DIR unless it's root '/'
if [[ "$TARGET_DIR" != "/" ]]; then
    TARGET_DIR="${TARGET_DIR%/}"
fi

OS_NAME=$(uname -s)
DELIM=$'\x1f'
SCANNED_AT=$(date -u +"%Y-%m-%d %H:%M:%S")

format_timestamp() {
    local ts="$1"
    if [[ -z "$ts" || "$ts" == "-" || "$ts" == "0" ]]; then
        echo ""
    elif [[ "$ts" =~ ^[0-9]+$ ]]; then
        if [[ "$OS_NAME" == "Darwin" || "$OS_NAME" == *"BSD"* ]]; then
            date -u -r "$ts" +"%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "$SCANNED_AT"
        else
            date -u -d "@$ts" +"%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "$SCANNED_AT"
        fi
    else
        echo "$ts"
    fi
}

# Find files and directories, ignoring symlinks (! -type l)
find "$TARGET_DIR" -mindepth 1 \( -type f -o -type d \) ! -type l 2>/dev/null | while IFS= read -r abs_path || [[ -n "$abs_path" ]]; do
    if [[ -z "$abs_path" ]]; then
        continue
    fi

    # Relative path calculation
    rel_path="${abs_path#"$TARGET_DIR"/}"
    rel_path="${rel_path//\\//}" # Normalizing slashes
    rel_path="${rel_path%/}"

    if [[ -z "$rel_path" ]]; then
        continue
    fi

    # Parent relative path calculation
    if [[ "$rel_path" == *"/"* ]]; then
        parent_rel_path="${rel_path%/*}"
    else
        parent_rel_path=""
    fi

    # Name and Extension
    filename="${rel_path##*/}"
    is_dir=false
    size_bytes=0
    ext=""

    if [[ -d "$abs_path" ]]; then
        is_dir=true
    else
        is_dir=false
        if [[ "$filename" == *.* && "$filename" != .* ]]; then
            ext="${filename##*.}"
            ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
        fi
    fi

    # Stat extraction
    created_at=""
    modified_at=""

    if [[ "$OS_NAME" == "Darwin" || "$OS_NAME" == *"BSD"* ]]; then
        # BSD stat
        size_bytes=$(stat -f "%z" "$abs_path" 2>/dev/null || echo 0)
        mtime_sec=$(stat -f "%m" "$abs_path" 2>/dev/null || echo 0)
        btime_sec=$(stat -f "%B" "$abs_path" 2>/dev/null || echo 0)

        modified_at=$(format_timestamp "$mtime_sec")
        created_at=$(format_timestamp "$btime_sec")
    else
        # GNU stat
        size_bytes=$(stat -c "%s" "$abs_path" 2>/dev/null || echo 0)
        mtime_sec=$(stat -c "%Y" "$abs_path" 2>/dev/null || echo 0)
        btime_sec=$(stat -c "%W" "$abs_path" 2>/dev/null || echo 0)

        modified_at=$(format_timestamp "$mtime_sec")
        if [[ "$btime_sec" != "0" && "$btime_sec" != "-" ]]; then
            created_at=$(format_timestamp "$btime_sec")
        fi
    fi

    # Timestamp Fallback
    if [[ -z "$created_at" ]]; then
        if [[ -n "$modified_at" ]]; then
            created_at="$modified_at"
        else
            created_at="$SCANNED_AT"
        fi
    fi
    if [[ -z "$modified_at" ]]; then
        modified_at="$SCANNED_AT"
    fi

    printf "%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s\n" \
        "$MEDIA_ID" "$DELIM" \
        "$filename" "$DELIM" \
        "$ext" "$DELIM" \
        "$rel_path" "$DELIM" \
        "$parent_rel_path" "$DELIM" \
        "$is_dir" "$DELIM" \
        "$size_bytes" "$DELIM" \
        "$created_at" "$DELIM" \
        "$modified_at"
done || true

exit 0
