#!/usr/bin/env bash
# Build a distributable ZIP of the page-marker editor for non-technical recipients.
#
# Usage:
#   git tag v0.1.0
#   ./scripts/release.sh
#
# Output:
#   versions/rx-pagemarker-editor-v0.1.0.zip
#
# Versioning method mirrors rx-ind-epub-gen: semver git tags (vX.Y.Z) are the
# single source of truth. pyproject.toml uses setuptools-scm to derive the
# Python package version from the same tag, so the wheel and the ZIP filename
# always agree.
#
# Preconditions enforced below: clean working tree, HEAD on a vX.Y.Z tag.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "error: working tree has uncommitted changes." >&2
  echo "       commit or stash before building a release." >&2
  exit 1
fi

if ! VERSION="$(git describe --tags --exact-match HEAD 2>/dev/null)"; then
  echo "error: HEAD is not on a tag." >&2
  echo "       create one first, e.g.:" >&2
  echo "         git tag v0.1.0" >&2
  echo "         git push --tags" >&2
  exit 1
fi

if ! [[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "error: tag '$VERSION' is not vX.Y.Z (semver) format." >&2
  exit 1
fi

PKG_NAME="rx-pagemarker-editor-${VERSION}"
STAGING="$(mktemp -d)"
PKG_DIR="${STAGING}/${PKG_NAME}"
trap 'rm -rf "${STAGING}"' EXIT

mkdir -p "${PKG_DIR}/examples"

cp tools/page-marker-editor.html "${PKG_DIR}/"
cp tools/pdf-splitter.html       "${PKG_DIR}/"
cp tools/help.html               "${PKG_DIR}/"
cp -R examples/.                 "${PKG_DIR}/examples/"
cp scripts/release-readme.md     "${PKG_DIR}/README.md"
echo "${VERSION}" > "${PKG_DIR}/VERSION"

mkdir -p versions
ZIP_PATH="${REPO_ROOT}/versions/${PKG_NAME}.zip"
if [[ -f "${ZIP_PATH}" ]]; then
  echo "error: versions/${PKG_NAME}.zip already exists." >&2
  echo "       a release for ${VERSION} was already built." >&2
  echo "       bump the tag (e.g., ${VERSION%.*}.$((${VERSION##*.} + 1))) or delete the existing file." >&2
  exit 1
fi
(cd "${STAGING}" && zip -rq "${ZIP_PATH}" "${PKG_NAME}")

SIZE="$(du -h "${ZIP_PATH}" | awk '{print $1}')"
SHA="$(shasum -a 256 "${ZIP_PATH}" | awk '{print $1}')"

echo "built  versions/${PKG_NAME}.zip  (${SIZE})"
echo "sha256 ${SHA}"
echo
echo "all releases in versions/:"
ls -1 versions/*.zip 2>/dev/null | sed 's|^|  |'
echo
echo "recipients: extract the ZIP and open page-marker-editor.html in a browser."
