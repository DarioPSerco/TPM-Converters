#!/bin/bash
USAGE_HELP="Usage: /bin/bash zip_to_package.sh <path to library root> <directory for output zip>"
if [[ ${#} != 2 ]]; then
  echo "${USAGE_HELP}"
  exit 1
fi

EOSIP_LIBRARY_ROOT=$(sed 's:/*$::' <(echo "${1}"))
OUTPUT_ZIP_DIR=$(sed 's:/*$::' <(echo "${2}"))

if [[ ! -d ${EOSIP_LIBRARY_ROOT} ]]; then
  echo "${USAGE_HELP}"
  echo "${EOSIP_LIBRARY_ROOT} does not exist"
  exit 1
fi

if [[ ! -d ${OUTPUT_ZIP_DIR} ]]; then
  echo "${USAGE_HELP}"
  echo "${OUTPUT_ZIP_DIR} does not exist"
  exit 1
fi

CONVERTER_VERSION=$(\
  grep -m1 -P "^__version__ ?=" "${EOSIP_LIBRARY_ROOT}"/eoSip_converter/__init__.py | \
  sed -E "s/^[^'\"]*['\"]([^'\"]*)['\"].*/\1/"
)

EOSIP_LIBRARY_NAME=$(basename "${EOSIP_LIBRARY_ROOT}")
cd "$(dirname "${EOSIP_LIBRARY_ROOT}")" || exit 1

ZIP_FILE="${OUTPUT_ZIP_DIR}"/eoSip_converter_v"${CONVERTER_VERSION}".zip

if [[ -f "${ZIP_FILE}" ]]; then
  rm "${ZIP_FILE}"
fi

zip -r "${ZIP_FILE}" "${EOSIP_LIBRARY_NAME}" \
    -x '*/__pycache__/*' \
    -x '*test*' \
    -x '*/.*' \
    -x 'eoSip_converter/build/*' \
    -x '*/*.egg-info/*' \
    -x 'eoSip_converter/nifi/*' \
    -x 'eoSip_converter/footprint_check.py' \
    -x '*/converter.log' \
    -x 'eoSip_converter/test_bi_creation.py' \
    > /dev/null

if [[ ! $? -eq 0 ]]
then
  echo "Zip to ${ZIP_FILE} failed"
  cd - > /dev/null || exit 1
  exit 1
fi
cd - > /dev/null || exit 1

echo "eoSip_converter library v${CONVERTER_VERSION} packaged and written to ${ZIP_FILE}"
