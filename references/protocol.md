<p align="right">
  <a href="protocol.zh_CN.md">简体中文</a> · <strong>English</strong>
</p>

# Cover-page return protocol

## Compatibility levels

1. **General compatibility:** a valid ESP32-C3 application can be installed and
   launched without a Launcher SDK. Reset or power-cycle returns to Launcher.
2. **Enhanced cover return:** while the play's existing cover/start page is
   active, Up Long requests an immediate return to the verified factory Launcher.

Enhanced return is optional. It must not weaken general compatibility.

## Input contract

- Trigger: the project's semantic Up Long event; about 1.5 seconds is the
  recommended interaction duration when the project needs a value.
- Scope: only the existing cover/start state.
- Non-scope: gameplay, settings, pause, results, diagnostics, and every other
  state.
- UI: no extra label, modal, or toast is required.
- Failure: log a diagnostic error and keep the play running.

## Boot contract

`launcher_contract_return_to_factory()` discovers the labeled `factory`
partition, verifies its image, selects it as the next boot partition, and
restarts. It returns only on failure.

Do not hardcode the factory address. Do not select an unverified image. Do not
mark the child application valid when the Launcher relies on one-shot OTA
rollback for reboot-to-Launcher compatibility.

This applies to everything linked into the play, not only its own code:
`components/`, `managed_components/`, extra component directories, and prebuilt
libraries. `esp_ota_mark_app_valid_cancel_rollback()` anywhere in the firmware
is a blocker. `esp_ota_set_boot_partition()`, `esp_https_ota()` and
`esp_https_ota_finish()` outside `launcher_contract` change the boot target and
need review. `scripts/audit_boot_control.py` checks both in source and in the
linked build.

## Acceptance checklist

- Cover page + Up Long: Launcher appears.
- Gameplay + Up Long: original play behavior remains.
- Settings/other states + Up Long: original play behavior remains.
- Boot-control audit of the release build: no blocker.
- Reset from the play: Launcher appears.
- Power-cycle from the play: Launcher appears.
- Missing/invalid factory in a controlled test: no reboot loop; error is logged.
