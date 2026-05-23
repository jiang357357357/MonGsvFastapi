#!/bin/bash

# MonGSV project packer for Linux.
# Uses tar.gz or 7z and reads [pack].EXCLUDE_PATTERNS from .monconfig.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find_workspace_root() {
    local dir="$1"
    while [[ -n "$dir" && "$dir" != "/" ]]; do
        if [[ -f "$dir/.monconfig" ]]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    return 1
}

read_pack_excludes() {
    local config_file="$1"
    local in_pack=false
    local in_excludes=false

    if [[ ! -f "$config_file" ]]; then
        return 0
    fi

    while IFS= read -r line || [[ -n "$line" ]]; do
        local trimmed="$line"
        trimmed="${trimmed#"${trimmed%%[![:space:]]*}"}"
        trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"

        if [[ "$trimmed" =~ ^\[.*\]$ ]]; then
            if $in_pack && $in_excludes; then
                break
            fi
            if [[ "$trimmed" == "[pack]" ]]; then
                in_pack=true
            else
                in_pack=false
            fi
            in_excludes=false
            continue
        fi

        if ! $in_pack; then
            continue
        fi

        if ! $in_excludes; then
            if [[ "$trimmed" == EXCLUDE_PATTERNS=* ]]; then
                in_excludes=true
                local inline_value="${trimmed#EXCLUDE_PATTERNS=}"
                inline_value="${inline_value#"${inline_value%%[![:space:]]*}"}"
                inline_value="${inline_value%"${inline_value##*[![:space:]]}"}"
                if [[ -n "$inline_value" && ! "$inline_value" =~ ^# ]]; then
                    EXCLUDE_PATTERNS+=("${inline_value%/}")
                fi
            fi
            continue
        fi

        if [[ -z "$trimmed" || "$trimmed" =~ ^# ]]; then
            continue
        fi

        if [[ ! "$line" =~ ^[[:space:]]+ ]]; then
            break
        fi

        EXCLUDE_PATTERNS+=("${trimmed%/}")
    done < "$config_file"
}

show_help() {
    echo "MonGSV packer for Linux"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -o, --output <file>    Output archive path"
    echo "  -s, --source <dir>     Source directory, defaults to workspace root"
    echo "  -t, --tar              Build tar.gz instead of 7z"
    echo "  -h, --help             Show help"
    echo ""
}

WORKSPACE_ROOT="$(find_workspace_root "$SCRIPT_DIR" || true)"
if [[ -z "$WORKSPACE_ROOT" ]]; then
    echo "Error: could not find workspace root via .monconfig"
    exit 1
fi

OUTPUT_FILE=""
SOURCE_DIR="$WORKSPACE_ROOT"
USE_TAR=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -s|--source)
            SOURCE_DIR="$2"
            shift 2
            ;;
        -t|--tar)
            USE_TAR=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "Error: source directory does not exist: $SOURCE_DIR"
    exit 1
fi

SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"
MONCONFIG_FILE="$SOURCE_DIR/.monconfig"
EXCLUDE_PATTERNS=()
read_pack_excludes "$MONCONFIG_FILE"

if [[ -z "$OUTPUT_FILE" ]]; then
    TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
    BASENAME="$(basename "$SOURCE_DIR")"
    DEFAULT_OUTPUT_DIR="$(dirname "$SOURCE_DIR")"
    if $USE_TAR; then
        OUTPUT_FILE="${DEFAULT_OUTPUT_DIR}/${BASENAME}_${TIMESTAMP}.tar.gz"
    else
        OUTPUT_FILE="${DEFAULT_OUTPUT_DIR}/${BASENAME}_${TIMESTAMP}.7z"
    fi
fi

OUTPUT_PARENT="$(dirname "$OUTPUT_FILE")"
mkdir -p "$OUTPUT_PARENT"
OUTPUT_DIR="$(cd "$OUTPUT_PARENT" && pwd)"
OUTPUT_FILE="$OUTPUT_DIR/$(basename "$OUTPUT_FILE")"

echo ""
echo "=================================================="
echo "  MonGSV Project Packer (Linux)"
echo "=================================================="
echo ""
echo "  Source: $SOURCE_DIR"
echo "  Config: $MONCONFIG_FILE"
echo "  Output: $OUTPUT_FILE"
echo "  Format: $([ "$USE_TAR" = true ] && echo "tar.gz" || echo "7z")"
echo "  Excludes: ${#EXCLUDE_PATTERNS[@]}"
echo ""

if [[ ${#EXCLUDE_PATTERNS[@]} -gt 0 ]]; then
    echo "[Exclude] Top-level directory matches:"
    found_any=false
    while IFS= read -r item; do
        name="$(basename "$item")"
        for pattern in "${EXCLUDE_PATTERNS[@]}"; do
            if [[ "$name" == "$pattern" ]] || [[ "$name" == $pattern ]]; then
                size="$(du -sh "$item" 2>/dev/null | cut -f1)"
                echo "  - $name (${size})"
                found_any=true
                break
            fi
        done
    done < <(find "$SOURCE_DIR" -mindepth 1 -maxdepth 1 -type d | sort)
    if ! $found_any; then
        echo "  - (none)"
    fi
    echo ""
fi

cd "$SOURCE_DIR"

if $USE_TAR; then
    EXCLUDE_ARGS=()
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        EXCLUDE_ARGS+=(--exclude="$pattern")
    done
    tar -czf "$OUTPUT_FILE" "${EXCLUDE_ARGS[@]}" .
else
    if ! command -v 7z >/dev/null 2>&1; then
        echo "Error: 7z not found. Please install p7zip-full."
        exit 1
    fi

    EXCLUDE_ARGS=()
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        EXCLUDE_ARGS+=("-xr!$pattern")
    done

    7z a -t7z -m0=lzma2 -mx=5 -bb0 "${EXCLUDE_ARGS[@]}" "$OUTPUT_FILE" .
fi

echo ""
echo "=================================================="
if [[ -f "$OUTPUT_FILE" ]]; then
    FILE_SIZE="$(du -h "$OUTPUT_FILE" 2>/dev/null | cut -f1)"
    echo "[Result] OK"
    echo "  Output: $OUTPUT_FILE"
    echo "  Size: $FILE_SIZE"
else
    echo "[Result] FAILED"
    exit 1
fi
echo "=================================================="
echo ""
