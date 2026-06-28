#!/usr/bin/env bash
# AppRun-style entrypoint executed when the user launches the AppImage.
#
# The AppImage runtime sets $APPDIR to the mounted root of the bundled
# filesystem. python-appimage installs CPython under $APPDIR/opt/python*/
# and our console-script `platterpus` ends up on the bundled bin/ PATH.

set -e

# Locate the bundled Python install (manylinux base is python3.11 today;
# fall back to whatever version python-appimage embedded if that changes).
APPDIR="${APPDIR:-$(dirname "$0")}"
PYTHON_BIN="$(ls "$APPDIR"/opt/python*/bin/python* 2>/dev/null | head -1)"

if [ -z "$PYTHON_BIN" ]; then
    echo "platterpus: could not find bundled Python interpreter" >&2
    exit 1
fi

# The bundled (manylinux) CPython ships with NO CA certificates, so every
# HTTPS request — most importantly the MusicBrainz disc-ID lookup — fails
# with "CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate".
# Point OpenSSL at the host's CA bundle if the caller hasn't set one. These
# paths cover the mainstream desktop-Linux layouts the project targets:
#   Fedora/Bazzite/RHEL : /etc/pki/tls/certs/ca-bundle.crt
#   Debian/Ubuntu       : /etc/ssl/certs/ca-certificates.crt
#   Arch/openSUSE       : /etc/ssl/certs/ca-certificates.crt or ca-bundle
#   Alpine/misc         : /etc/ssl/cert.pem
if [ -z "${SSL_CERT_FILE:-}" ]; then
    for _ca in \
        /etc/pki/tls/certs/ca-bundle.crt \
        /etc/ssl/certs/ca-certificates.crt \
        /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem \
        /etc/ssl/ca-bundle.pem \
        /etc/ssl/cert.pem; do
        if [ -f "$_ca" ]; then
            export SSL_CERT_FILE="$_ca"
            break
        fi
    done
fi
if [ -z "${SSL_CERT_DIR:-}" ] && [ -d /etc/ssl/certs ]; then
    export SSL_CERT_DIR=/etc/ssl/certs
fi

# Run the package as a module so we get a stable entry point regardless
# of whether the console script was installed under bin/.
exec "$PYTHON_BIN" -m platterpus "$@"
