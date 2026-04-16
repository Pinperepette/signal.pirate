#!/bin/bash
# VULN-06: MITM Setup - Demonstrates lack of certificate pinning
# and the TrustAll pattern documented in the official README
source "$(dirname "$0")/00-common.sh"

banner "VULN-06: MITM - NO CERTIFICATE PINNING"
check_device

echo "  Questa dimostrazione verifica 3 cose:"
echo ""
echo "  1. Assenza di certificate pinning nel codice"
echo "  2. HttpClient senza SSL customization"
echo "  3. TrustAllX509TrustManager nella documentazione ufficiale"
echo ""

# 1. Verifica network_security_config
banner "1. Network Security Config"
CONFIG=$(cat "$(dirname "$0")/../../av-app-android-wallet-ui/network-logic/src/main/res/xml/network_security_config.xml" 2>/dev/null)

if echo "$CONFIG" | grep -q "pin-set"; then
    fail "Certificate pinning trovato"
else
    ok "Nessun certificate pinning in network_security_config.xml"
    echo "$CONFIG" | grep -v "^<!--" | grep -v "^$" | grep -v "Copyright" | sed 's/^/       /'
fi

# 2. Verifica HttpClient
banner "2. Ktor HttpClient Configuration"
NETMODULE="$(dirname "$0")/../../av-app-android-wallet-ui/network-logic/src/main/java/eu/europa/ec/networklogic/di/NetworkModule.kt"

if [ -f "$NETMODULE" ]; then
    if grep -q "sslManager\|trustManager\|certificatePinner\|hostnameVerifier" "$NETMODULE"; then
        fail "SSL customization trovata nel NetworkModule"
    else
        ok "HttpClient(Android) senza SSL customization"
        info "Nessun certificate pinning, nessun custom TrustManager"
        echo ""
        grep -A 15 "fun provideHttpClient" "$NETMODULE" | sed 's/^/       /'
    fi
fi

# 3. TrustAll nel README
banner "3. TrustAllX509TrustManager nella documentazione"
BUILD_DOC="$(dirname "$0")/../../av-app-android-wallet-ui/docs/how_to_build.md"

if [ -f "$BUILD_DOC" ]; then
    if grep -q "TrustAllX509TrustManager\|trustAllCerts\|HostnameVerifier.*true" "$BUILD_DOC"; then
        ok "TrustAllX509TrustManager trovato in docs/how_to_build.md"
        info "Pattern che disabilita tutta la validazione SSL:"
        echo ""
        grep -n "trustAllCerts\|TrustAllX509\|hostnameVerifier\|HostnameVerifier" "$BUILD_DOC" | sed 's/^/       /'
    else
        fail "Pattern non trovato nella documentazione"
    fi
fi

# 4. Intercettazione pratica con mitmproxy
banner "4. Setup MITM con mitmproxy (opzionale)"
echo "  Per intercettare il traffico in pratica:"
echo ""
echo "  # Installa mitmproxy"
echo "  brew install mitmproxy"
echo ""
echo "  # Avvia il proxy"
echo "  mitmproxy --listen-port 8080"
echo ""
echo "  # Configura proxy sull'emulatore"
echo "  adb shell settings put global http_proxy 10.0.2.2:8080"
echo ""
echo "  # Installa il certificato CA di mitmproxy"
echo "  # (su API < 24 o debug build con android:debuggable=true)"
echo "  adb push ~/.mitmproxy/mitmproxy-ca-cert.cer /sdcard/"
echo "  adb shell am start -a android.settings.SECURITY_SETTINGS"
echo "  # Installa da Settings > Security > Install from storage"
echo ""
echo "  # Avvia l'app e osserva il traffico"
echo "  # Tutti i token OAuth, authorization codes, e credential"
echo "  # responses sono visibili in chiaro nel proxy."
echo ""
echo "  # Rimuovi proxy dopo il test"
echo "  adb shell settings put global http_proxy :0"
echo ""

# Verifica se mitmproxy e' installato
if command -v mitmproxy &> /dev/null; then
    ok "mitmproxy installato ($(mitmproxy --version 2>&1 | head -1))"
    info "Pronto per intercettazione live"
else
    info "mitmproxy non installato (brew install mitmproxy per il test live)"
fi

banner "RISULTATO: Nessun certificate pinning, MITM documentato nel README"
