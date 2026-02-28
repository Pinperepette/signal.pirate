// BiometricKit.framework — classi principali
// Estratto via Python objc bridge

@interface BiometricKit
  // --- Enrollment (registrazione volto) ---
  - enroll_withOptions_
  - enroll_forUser_withOptions_
  - enrollFeedback_client_
  - enrollResult_details_client_

  // --- Matching (riconoscimento) ---
  - match_
  - match_withOptions_
  - matchResult_details_client_

  // --- Identity management ---
  - identities_
  - removeIdentity_
  - updateIdentity_
  - getMaxIdentityCount_
@end

@interface BiometricKitIdentity
  - uuid                    // identificativo unico
  - name                    // "Il mio volto"
  - type                    // Face ID o Touch ID
  - matchCount              // quante volte ha matchato — INCREMENTA
  - matchCountContinuous    // match consecutivi
  - updateCount             // aggiornamenti del template
  - accessory               // occhiali, mascherina
@end

@interface BiometricKitXPCClient
  // Il client che parla col demone biometrickd via XPC
  - connect
  - disconnect
  - match_withOptions_async_withReply_
  - enroll_forUser_withOptions_async_withReply_
  - listAccessories_         // occhiali, mascherine, accessori
  - forceBioLockoutForUser_withOptions_  // 5 tentativi = bloccato
  - getBioLockoutState_forUser_
  - pullCaptureBuffer
  - pullDebugImageData_rotated_imageWidth_imageHeight_
@end
