#!/bin/bash

set -euo pipefail

REPO="Shivam-20/emailExpensesTracker"
BASE_URL="https://github.com/$REPO/releases/download/latest"
MODELS_DIR="models"
FORCE=false
SPECIFIC_MODEL=""

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Download trained models from GitHub releases.

OPTIONS:
    --force           Force redownload even if files exist
    --model MODEL     Download specific model (minilm, tfidf, all)
    -h, --help        Show this help message

EXAMPLES:
    $0                  Download all models
    $0 --force          Force redownload all models
    $0 --model minilm  Download only minilm model
    $0 --model tfidf   Download only tfidf model
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        --model)
            SPECIFIC_MODEL="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

mkdir -p "$MODELS_DIR"
mkdir -p "$MODELS_DIR/lightweight"

download_file() {
    local url="$1"
    local dest="$2"
    local filename
    filename=$(basename "$dest")

    if [[ -f "$dest" ]] && [[ "$FORCE" == "false" ]]; then
        echo "Skipping $filename (already exists, use --force to redownload)"
        return 0
    fi

    echo "Downloading $filename..."
    if curl -sL --fail -o "$dest" "$url"; then
        echo "Downloaded $filename"
    else
        echo "Failed to download $filename"
        rm -f "$dest"
        return 1
    fi
}

download_tarball() {
    local url="$1"
    local dest_dir="$2"
    local archive
    archive=$(mktemp)

    echo "Downloading archive..."
    if ! curl -sL --fail -o "$archive" "$url"; then
        echo "Failed to download archive"
        rm -f "$archive"
        return 1
    fi

    echo "Extracting to $dest_dir..."
    mkdir -p "$dest_dir"
    tar -xzf "$archive" -C "$dest_dir" --strip-components=1
    rm -f "$archive"
    echo "Extracted successfully"
}

fetch_release_info() {
    curl -sL "https://api.github.com/repos/$REPO/releases/latest"
}

get_asset_download_url() {
    local asset_name="$1"
    fetch_release_info | python3 -c "
import sys, json
data = json.load(sys.stdin)
for asset in data.get('assets', []):
    if asset['name'] == '$asset_name':
        print(asset['browser_download_url'])
        break
" 2>/dev/null || echo ""
}

if [[ "$SPECIFIC_MODEL" == "tfidf" ]] || [[ "$SPECIFIC_MODEL" == "" ]]; then
    echo "=== Downloading TF-IDF/NB model ==="
    DEST="$MODELS_DIR/nb_tfidf_model.joblib"
    URL=$(get_asset_download_url "nb_tfidf_model.joblib")
    if [[ -n "$URL" ]]; then
        download_file "$URL" "$DEST"
    else
        download_file "$BASE_URL/nb_tfidf_model.joblib" "$DEST" || true
    fi
fi

if [[ "$SPECIFIC_MODEL" == "minilm" ]] || [[ "$SPECIFIC_MODEL" == "" ]]; then
    echo "=== Downloading MiniLM model ==="
    DEST_DIR="$MODELS_DIR/lightweight/minilm"
    URL=$(get_asset_download_url "minilm.tar.gz")
    if [[ -n "$URL" ]]; then
        if [[ -d "$DEST_DIR" ]] && [[ "$FORCE" == "false" ]]; then
            echo "Skipping minilm (already exists, use --force to redownload)"
        else
            download_tarball "$URL" "$DEST_DIR"
        fi
    else
        download_tarball "$BASE_URL/minilm.tar.gz" "$DEST_DIR" 2>/dev/null || echo "Warning: minilm model not available in release yet"
    fi
fi

echo "=== Download complete ==="
ls -la "$MODELS_DIR"/
