#!/bin/bash
# Common functions for all demo scripts

ADB="${ANDROID_HOME:-$HOME/Library/Android/sdk}/platform-tools/adb"
PKG="com.scytales.av.dev"
PREFS="/data/data/$PKG/shared_prefs/eudi-wallet.xml"
DOCDB="/data/data/$PKG/no_backup/EudiWalletDocumentManager.db"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

ok()     { echo -e "  ${GREEN}[PASS]${NC} $1"; }
fail()   { echo -e "  ${RED}[FAIL]${NC} $1"; }
info()   { echo -e "  ${YELLOW}[*]${NC} $1"; }
banner() { echo -e "\n${CYAN}=== $1 ===${NC}\n"; }

read_prefs() { $ADB shell "run-as $PKG cat $PREFS" 2>/dev/null; }

write_prefs() {
    $ADB push "$1" /data/local/tmp/eudi-wallet.xml > /dev/null 2>&1
    $ADB shell "run-as $PKG cp /data/local/tmp/eudi-wallet.xml $PREFS" 2>/dev/null
}

restart_app() {
    $ADB shell am force-stop $PKG 2>/dev/null
    sleep 1
    $ADB shell monkey -p $PKG -c android.intent.category.LAUNCHER 1 > /dev/null 2>&1
    sleep 2
}

check_device() {
    if ! $ADB get-state > /dev/null 2>&1; then
        fail "Nessun device/emulatore connesso"; exit 1
    fi
    if ! $ADB shell pm list packages 2>/dev/null | grep -q "$PKG"; then
        fail "App $PKG non installata"; exit 1
    fi
    ok "Device connesso, app presente"
}
