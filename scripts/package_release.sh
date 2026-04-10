#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd -- "${SCRIPT_PATH%/*}" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${REPO_ROOT}/dist"
VERSION=""
DRY_RUN=0

usage() {
  cat <<EOF
Usage: scripts/package_release.sh [options]

Create distributable Sengent source archives for GitHub Releases.

Options:
  --output-dir <path>   Output directory for archives (default: dist/)
  --version <value>     Override version string used in archive names
  --dry-run             Print planned archive names without creating them
  --help                Show this help text
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="${2:?missing value for --output-dir}"
      shift 2
      ;;
    --version)
      VERSION="${2:?missing value for --version}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${VERSION}" ]]; then
  VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "${REPO_ROOT}/pyproject.toml" | head -n 1)"
fi

if [[ -z "${VERSION}" ]]; then
  echo "Failed to resolve version from pyproject.toml; pass --version explicitly." >&2
  exit 2
fi

BUNDLE_ROOT="sengent-${VERSION}"
TAR_PATH="${OUTPUT_DIR}/${BUNDLE_ROOT}.tar.gz"
ZIP_PATH="${OUTPUT_DIR}/${BUNDLE_ROOT}.zip"

echo "Repo root: ${REPO_ROOT}"
echo "Version: ${VERSION}"
echo "Output dir: ${OUTPUT_DIR}"
echo "tar.gz: ${TAR_PATH}"
echo "zip: ${ZIP_PATH}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "Dry run only; no archives created."
  exit 0
fi

mkdir -p "${OUTPUT_DIR}"
git -C "${REPO_ROOT}" archive --format=tar.gz --prefix="${BUNDLE_ROOT}/" -o "${TAR_PATH}" HEAD
git -C "${REPO_ROOT}" archive --format=zip --prefix="${BUNDLE_ROOT}/" -o "${ZIP_PATH}" HEAD

echo "Release archives created:"
echo "  - ${TAR_PATH}"
echo "  - ${ZIP_PATH}"
