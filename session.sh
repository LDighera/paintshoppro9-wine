#!/bin/bash
# Runs only inside the offline namespace; no host service or global Wine stop.
set -euo pipefail
[[ $WINEPREFIX == /trial/prefix && $WINESERVER == /wine/bin/wineserver ]] || exit 2
[[ $(wine --version) == wine-11.14 ]] || { printf 'Expected the documented Wine 11.14 build.\n' >&2; exit 2; }
case ${1-} in
    initialize)
        [[ $# == 1 ]] || exit 2
        wineboot -u
        wineserver -w
        printf 'PSP9-PREFIX-INITIALIZED\n'
        ;;
    install)
        [[ $# == 2 ]] || exit 2
        cd /installer
        case ${2,,} in
            *.msi) wine msiexec /i "$2" ;;
            *.exe) wine "$2" ;;
            *) exit 2 ;;
        esac
        wineserver -w
        printf 'PSP9-INSTALLER-CLOSED: check installation path before running.\n'
        ;;
    run)
        [[ $# == 1 ]] || exit 2
        cd '/trial/prefix/drive_c/PSP9'
        result=0
        wine 'Z:\test\bootstrap.exe' --psp9 || result=$?
        # A nonzero child result remains failure even if wineserver exits cleanly.
        wineserver -w
        [[ $result == 0 ]] || exit "$result"
        printf 'PSP9-NORMAL-EXIT\n'
        ;;
    synthetic)
        [[ $# == 1 ]] || exit 2
        wineboot -u
        wineserver -w
        wine 'Z:\test\worker-test.exe' selftest
        wine 'Z:\test\worker-test.exe' baseline
        status=0
        wine 'Z:\test\bootstrap.exe' --reject-helper > /trial/rejection.log 2>&1 || status=$?
        [[ $status == 2 ]] && grep -q '^REMOTE_LOAD_FAILED' /trial/rejection.log || exit 2
        if grep -Eq 'HELPER_READY=1|CASE=|CHILD_NORMAL_EXIT=' /trial/rejection.log; then exit 2; fi
        wine 'Z:\test\bootstrap.exe' --synthetic
        wineserver -w
        printf 'PSP9-SYNTHETIC-PASSED\n'
        ;;
    *) exit 2 ;;
esac
