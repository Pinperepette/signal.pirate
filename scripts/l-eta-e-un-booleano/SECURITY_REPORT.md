# Security Assessment Report
# EU Age Verification (AV) Android Wallet Application

**Repository:** https://github.com/eu-digital-identity-wallet/av-app-android-wallet-ui
**Date:** 2026-04-16
**Build tested:** devDebug (commit latest main)
**Platform:** Android API 30 emulator (x86_64)

---

## Executive Summary

The Age Verification Android Wallet application contains multiple security vulnerabilities at the implementation level. More critically, the application's architecture and the underlying verification model contain fundamental design flaws that cannot be resolved without a complete redesign of the trust chain.

All findings were verified with automated scripts on an Android emulator using the project's own test infrastructure (`test.issuer.dev.ageverification.dev`).

---

## Findings

### VULN-01: PIN Not Bound to Credential Vault (Critical)

**Files:**
- `authentication-logic/.../storage/PrefsPinStorageProvider.kt:64-79`
- `common-feature/.../interactor/QuickPinInteractor.kt:52`

**Description:**
The user PIN is encrypted with AES-256-GCM via Android Keystore and stored as `PinEnc` + `PinIv` in SharedPreferences. However, the PIN is not cryptographically bound to the credential vault (`EudiWalletDocumentManager.db`).

Removing the `PinEnc` and `PinIv` entries from the SharedPreferences file and restarting the app causes `hasPin()` to return `false`, presenting the onboarding flow where a new PIN can be set. The credentials in the wallet core remain intact and accessible under the new PIN.

**Impact:** An attacker with physical or ADB access can reset the PIN without invalidating stored credentials, gaining full access to age verification attestations.

**Proof:** See `scripts/01-pin-bypass.sh`

---

### VULN-02: Client-Side Rate Limiting (High)

**Files:**
- `authentication-logic/.../storage/PrefsPinStorageProvider.kt:106-132`
- `authentication-logic/.../controller/storage/PinStorageController.kt:37-94`

**Description:**
Failed PIN attempts are tracked via `PinFailedAttempts` (integer) and lockout duration via `PinLockoutUntil` (timestamp) in the same SharedPreferences file. The progressive lockout (1 min to 8 hours) can be instantly reset by setting both values to `0`.

**Impact:** Unlimited brute-force attempts against the 6-digit PIN (1,000,000 combinations). Combined with the fact that the PIN validation is a simple string comparison (`retrievePin() == pin` at line 62), an automated attack is trivial.

**Proof:** See `scripts/02-ratelimit-bypass.sh`

---

### VULN-03: Biometric Authentication Bypass (High)

**Files:**
- `authentication-logic/.../storage/PrefsBiometryStorageProvider.kt:57-68`

**Description:**
The biometric authentication toggle is stored as a plain boolean `UseBiometricsAuth` in SharedPreferences. Setting it to `false` disables biometric authentication entirely.

**Impact:** On a device with biometric auth enabled, an attacker can downgrade to PIN-only authentication (which can then be bypassed via VULN-01 or brute-forced via VULN-02).

**Proof:** See `scripts/03-biometric-bypass.sh`

---

### VULN-04: False Encryption - Obfuscation Presented as Cryptography (Medium)

**Files:**
- `business-logic/.../controller/storage/PrefsController.kt:199-201`
- `business-logic/.../extension/StringExtensions.kt:186-212`

**Description:**
The code comments state "Shared preferences are encrypted" (PrefsController.kt:194). In reality, strings are:
1. Base64-encoded
2. "Shuffled" using a Fisher-Yates shuffle with a hardcoded seed `[1, 3, 5, 7, 9, 2, 4, 6, 8]`

This is trivially reversible. The `CryptoAlias` (which references the Android Keystore key used for PIN encryption) can be decoded with 5 lines of Python.

**Impact:** False sense of security. Any value stored via `PrefsController.setString()` is recoverable by anyone who reads the source code (which is public).

**Proof:** See `scripts/04-decode-shuffle.py`

---

### VULN-05: Document Keys Do Not Require User Authentication (Critical)

**Files:**
- `core-logic/src/dev/java/.../config/WalletCoreConfigImpl.kt:40-41`
- `core-logic/.../controller/WalletCorePresentationController.kt:365-399`

**Description:**
The wallet configuration sets `userAuthenticationRequired = false` for document key creation:

```kotlin
configureDocumentKeyCreation(
    userAuthenticationRequired = false,  // Line 41
    ...
)
```

This means the cryptographic keys used to sign credential presentations in the Android Keystore do not require user authentication (PIN, biometric, or device credential) to be used. The presentation controller checks this flag at line 365 and skips authentication entirely when it is `false`.

**Impact:** Any process with access to the app's context can sign and present credentials without any user interaction. This is the most critical finding because it means the credential presentation is not bound to user presence.

---

### VULN-06: No Certificate Pinning + MITM Pattern in Official Documentation (Medium)

**Files:**
- `network-logic/src/main/res/xml/network_security_config.xml`
- `network-logic/.../di/NetworkModule.kt:49-67`
- `docs/how_to_build.md:134-186`

**Description:**
The network security configuration only disables cleartext traffic (`cleartextTrafficPermitted="false"`). There is:
- No certificate pinning configured
- No custom TrustManager implementation
- The Ktor HTTP client at `NetworkModule.kt:50` uses default Android engine with no SSL customization

The official documentation (`how_to_build.md`) provides a complete `TrustAllX509TrustManager` implementation with `HostnameVerifier { _, _ -> true }`, instructing developers to trust all certificates. While intended for local development, this pattern in official documentation normalizes insecure practices.

On a debug build on an emulator or rooted device, installing a custom CA certificate in the user trust store is sufficient to intercept all HTTPS traffic between the app and the issuer/verifier services.

**Impact:** On rooted devices or with user-installed CA certificates (Android < 7 or debug builds), all communication between wallet, issuer, and verifier can be intercepted, including authorization codes and credential tokens.

**Proof:** See `scripts/05-mitm-setup.sh`

---

### VULN-07: Credential Database Not Encrypted (Medium)

**Files:**
- `no_backup/EudiWalletDocumentManager.db`

**Description:**
The credential database is a standard SQLite database stored in the app's `no_backup` directory. It is not encrypted (no SQLCipher, no Android EncryptedFile). On a rooted device or emulator, the entire database (containing signed CBOR credentials) can be extracted via:

```
adb shell "run-as com.scytales.av.dev cat .../EudiWalletDocumentManager.db" > dump.db
```

**Impact:** Signed age verification attestations can be extracted from the device and potentially replayed or transferred.

**Proof:** See `scripts/06-extract-credentials.sh`

---

### VULN-08: Credential Replay / Portability to Chrome Extension (Critical - Design)

**Files:**
- `core-logic/.../config/WalletCoreConfig.kt:196-199`
- `core-logic/.../config/WalletCoreConfigImpl.kt:40-41,47-49`
- `no_backup/EudiWalletDocumentManager.db`

**Description:**
The combination of VULN-05 (no user auth for keys), VULN-07 (unencrypted database), and the credential issuance configuration creates a credential replay attack surface:

1. **30 pre-generated credentials per issuance** (`CredentialPolicy.OneTimeUse`, `numberOfCredentials = 30` at WalletCoreConfig.kt:198-199). Each enrollment generates 30 single-use credentials, all stored in the SQLite database.

2. **Credentials extractable from database** as CBOR payloads containing `age_over_18` boolean and issuer signature.

3. **Verifier uses RedirectUri scheme** (WalletCoreConfigImpl.kt:47-49), not mutual TLS. The verifier cannot cryptographically verify the identity of the presenting party.

4. **No per-presentation user binding**. The `userAuthenticationRequired = false` setting means credential presentation requires no biometric or PIN at the cryptographic level.

This makes it technically feasible to:
- Extract credentials from an emulator/rooted device
- Build a Chrome extension that detects verifier QR codes
- Respond with a valid OpenID4VP presentation using extracted credentials
- The verifier would accept the response as valid

On non-rooted devices, the key material remains in hardware Keystore, but can still be used without user authentication by any process with app context access.

**Impact:** The entire verification flow can potentially be replicated outside the app. The verifier cannot distinguish a legitimate app presentation from a replay or a Chrome extension.

**Proof:** See `scripts/08-credential-replay-poc.sh`

---

## Architectural Design Flaw

### The "Trust Me Bro" Problem

Beyond the implementation vulnerabilities, the system has a fundamental architectural issue that cannot be fixed without redesigning the trust model.

**Pre-age-verification:**
```
Website: "Are you over 18?"
User: "Yes."
```

**Post-age-verification:**
```
Website: "Are you over 18?"
App: "Yes." (signed attestation)
```

The verifier receives a single boolean (`age_over_18 = true/false`) signed by a trusted issuer. The cryptographic signature guarantees that a trusted issuer said "yes" -- it does NOT guarantee that:

1. The person presenting the attestation is the person who enrolled
2. The PIN/biometric wasn't bypassed before presentation
3. The credential wasn't extracted and replayed from another device
4. The person is actually present at the time of presentation

**We demonstrated this concretely:** we obtained an `age_over_18` attestation from the official test issuer without presenting any identity document, without biometric verification, and without any age check. The app displays the credential with an "18+" badge and a checkmark, ready to present to verifiers.

**The paradox:** the only way to fix this would be to cryptographically bind the key to the person at presentation time (biometric binding per-transaction). But this would enable cross-site tracking -- which is exactly what the system promises not to do.

---

## Test Environment

| Component | Version |
|-----------|---------|
| App | av-app-android-wallet-ui (latest main, devDebug) |
| Android SDK | 36 (compile) / 30 (test device) |
| Emulator | Android API 30, Google APIs, x86_64 |
| Test Issuer | test.issuer.dev.ageverification.dev |
| Test Verifier | verifier.ageverification.dev |

---

## Remediation Recommendations

| Finding | Recommendation | Complexity |
|---------|---------------|------------|
| VULN-01 | Bind PIN to credential vault via key derivation | High |
| VULN-02 | Move rate limiting server-side or use hardware-backed counter | Medium |
| VULN-03 | Use Keystore-backed biometric binding, not a boolean flag | Medium |
| VULN-04 | Use EncryptedSharedPreferences or remove false "encrypted" comments | Low |
| VULN-05 | Set `userAuthenticationRequired = true` | Low (code change) / High (UX impact) |
| VULN-06 | Implement certificate pinning; remove TrustAll from docs | Medium |
| VULN-07 | Use SQLCipher or Android EncryptedFile for credential DB | Medium |
| VULN-08 | Implement device binding + per-presentation auth + credential non-transferability | Very High |
| Design | Requires fundamental protocol redesign with per-presentation binding | Very High |
