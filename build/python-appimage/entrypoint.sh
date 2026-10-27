#!/usr/bin/env bash
# AppRun-style entrypoint executed when the user launches the AppImage.
#
# The AppImage runtime sets $APPDIR to the mounted root of the bundled
# filesystem. python-appimage installs CPython under $APPDIR/opt/python*/
# and our console-script `platterpus` ends up on the bundled bin/ PATH.

# `-u` too (review 2026-10-27, item 3.6): a misspelt variable stops the launch
# with its name instead of expanding to nothing. Safe here because every
# variable this file reads from outside is read with a default (`${APPDIR:-…}`,
# `${SSL_CERT_FILE:-}`, `${SSL_CERT_DIR:-}`). python-appimage pastes this file
# into AppRun after its own preamble, so the option takes effect from here on,
# and `exec` at the end means nothing of AppRun runs after it. `pipefail` is on
# as well, since the interpreter lookup below no longer pipes `ls` into
# `head -1` (ShellCheck SC2012, added to CI on 2026-10-27): that early-exiting
# pipe was the one reason this file had to leave pipefail off.
set -euo pipefail

# Locate the bundled Python install (manylinux base is python3.11 today;
# fall back to whatever version python-appimage embedded if that changes).
APPDIR="${APPDIR:-$(dirname "$0")}"
# The first match of the glob, in the shell's sorted order, which is the order
# `ls` listed them in. Reading the glob directly means a name with odd
# characters can't be split or mangled, and nothing is parsed out of `ls`. An
# unmatched glob stays literal, so `-f` also covers "nothing is there".
PYTHON_BIN=""
for candidate in "$APPDIR"/opt/python*/bin/python*; do
    if [ -f "$candidate" ]; then
        PYTHON_BIN="$candidate"
        break
    fi
done

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
