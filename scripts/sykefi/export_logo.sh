#!/usr/bin/env bash
# Generates the raster icon assets for the sykefi build from the SYKE logo SVG.
#
# Output layout matches upstream QField's APP_ICON_PATH convention
# (see CMakeLists.txt / src/app/CMakeLists.txt):
#   platform/sykefi/icons/qfield_logo.svg                   <- source (in-app logo, Linux icon)
#   platform/sykefi/icons/qfield_logo.ico                   <- Windows executable icon
#   platform/sykefi/icons/android/drawable-<dpi>/qfield_logo.png
#   platform/sykefi/icons/android/drawable/qfield_logo_vector.xml  <- Android adaptive icon + splash
#
# Requires: ImageMagick 7 (`magick`) with librsvg or inkscape delegate, python3 with Pillow.

set -euo pipefail

ICON_DIR="$(cd "$(dirname "$0")/../.." && pwd)/platform/sykefi/icons"
APP_ICON="${APP_ICON:-qfield_logo}"
SRC_SVG="${ICON_DIR}/${APP_ICON}.svg"
BASE_SIZE=48 # Android launcher icon size at mdpi (dp)

if [[ ! -f "${SRC_SVG}" ]]; then
	echo "Error: source SVG '${SRC_SVG}' not found" >&2
	exit 1
fi

# Android launcher icons, densities as in ANDROID_DRAWABLE_DENSITIES (root CMakeLists.txt)
declare -A DENSITIES=(
	[mdpi]=1
	[hdpi]=1.5
	[xhdpi]=2
	[xxhdpi]=3
	[xxxhdpi]=4
)
for density in "${!DENSITIES[@]}"; do
	size=$(awk -v b="${BASE_SIZE}" -v s="${DENSITIES[$density]}" 'BEGIN { printf "%d", b * s }')
	outdir="${ICON_DIR}/android/drawable-${density}"
	mkdir -p "${outdir}"
	echo "Android ${density}: ${size}x${size}"
	magick -background none -density 384 "${SRC_SVG}" -resize "${size}x${size}" "${outdir}/${APP_ICON}.png"
done

# Windows multi-size .ico (same sizes as upstream images/icons/qfield_logo.ico).
# Rendered at 256px by ImageMagick, assembled by Pillow so entries are PNG-compressed
# (ImageMagick stores them as uncompressed BMP, making the .ico ~10x larger).
echo "Windows: ${APP_ICON}.ico"
TMP_PNG="$(mktemp --suffix=.png)"
trap 'rm -f "${TMP_PNG}"' EXIT
magick -background none -density 384 "${SRC_SVG}" -resize 256x256 "${TMP_PNG}"
python3 - "${TMP_PNG}" "${ICON_DIR}/${APP_ICON}.ico" <<'PY'
import sys
from PIL import Image
img = Image.open(sys.argv[1]).convert("RGBA")
img.save(sys.argv[2], format="ICO", sizes=[(256, 256), (48, 48), (32, 32), (24, 24), (16, 16)])
PY

# Android VectorDrawable (adaptive launcher icon and splash screen)
echo "Android vector: drawable/${APP_ICON}_vector.xml"
mkdir -p "${ICON_DIR}/android/drawable"
python3 "$(dirname "$0")/svg_to_vector.py" "${SRC_SVG}" "${ICON_DIR}/android/drawable/${APP_ICON}_vector.xml"

echo "Done."
