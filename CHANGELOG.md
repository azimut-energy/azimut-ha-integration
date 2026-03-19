# Changelog

## [1.4.0](https://github.com/azimut-energy/azimut-ha-integration/compare/azimut-energy-v1.3.1...azimut-energy-v1.4.0) (2026-03-19)


### Features

* Add total solar power/energy computed sensors + clarify translations for PV/MPPT ([#28](https://github.com/azimut-energy/azimut-ha-integration/issues/28)) ([b0ee145](https://github.com/azimut-energy/azimut-ha-integration/commit/b0ee145cd715a958d3c11c56803e6c762ae73f96))

## [1.3.1](https://github.com/azimut-energy/azimut-ha-integration/compare/azimut-energy-v1.3.0...azimut-energy-v1.3.1) (2026-01-23)


### Bug Fixes

* enhance binary sensor support with discovery  ([#24](https://github.com/azimut-energy/azimut-ha-integration/issues/24)) ([2dc44e0](https://github.com/azimut-energy/azimut-ha-integration/commit/2dc44e048b56f3547a68fdee241efdc5035a139e))

## [1.3.0](https://github.com/azimut-energy/azimut-ha-integration/compare/azimut-energy-v1.2.1...azimut-energy-v1.3.0) (2026-01-16)


### Features

* **binary_sensor:** add binary sensor definitions support ([#22](https://github.com/azimut-energy/azimut-ha-integration/issues/22)) ([88f9445](https://github.com/azimut-energy/azimut-ha-integration/commit/88f9445e34876704b5f8f58e10abdda654bd401f))
* **types:** add comprehensive type annotations ([c5ecc4b](https://github.com/azimut-energy/azimut-ha-integration/commit/c5ecc4ba6a2cc17b1f1745c90e587bc8ad8c2a87))

## [1.2.1](https://github.com/azimut-energy/azimut-ha-integration/compare/azimut-energy-v1.2.0...azimut-energy-v1.2.1) (2026-01-11)


### Bug Fixes

* **mqtt:** sensors remain available on MQTT disconnect ([be4ba6e](https://github.com/azimut-energy/azimut-ha-integration/commit/be4ba6e76a039362165a88bab88917a2580961d7))


### Documentation

* add CLAUDE.md for AI assistant guidance ([fc7a399](https://github.com/azimut-energy/azimut-ha-integration/commit/fc7a399b1b370d082bba41a6087da1160d8871ca))

## [1.2.0](https://github.com/azimut-energy/azimut-ha-integration/compare/azimut-energy-v1.1.4...azimut-energy-v1.2.0) (2026-01-10)


### Features

* **mqtt:** add republish command topic support on reconnect ([#15](https://github.com/azimut-energy/azimut-ha-integration/issues/15)) ([cbc5be5](https://github.com/azimut-energy/azimut-ha-integration/commit/cbc5be5e47d286fad0da90638833f24be5c1aa28))


### Bug Fixes

* **lint:** remove unused imports in test files ([#13](https://github.com/azimut-energy/azimut-ha-integration/issues/13)) ([2d7c3d9](https://github.com/azimut-energy/azimut-ha-integration/commit/2d7c3d9b042f10b4dd4f0b2041ee7d22bfb0ddb3))

## [1.1.4](https://github.com/azimut-energy/azimut-ha-integration/compare/azimut-energy-v1.1.3...azimut-energy-v1.1.4) (2026-01-09)


### Bug Fixes

* documentation/help urls are pointing to wrong github namespace ([#10](https://github.com/azimut-energy/azimut-ha-integration/issues/10)) ([00f8d33](https://github.com/azimut-energy/azimut-ha-integration/commit/00f8d3384e8c648895e66f1c7451d4d143e8c6a3))

## [1.1.3](https://github.com/azimut-energy/azimut-ha-integration/compare/azimut-energy-v1.1.2...azimut-energy-v1.1.3) (2026-01-09)


### Bug Fixes

* **ci:** Fix zip structure to have files at root without folder wrapper ([#8](https://github.com/azimut-energy/azimut-ha-integration/issues/8)) ([111b237](https://github.com/azimut-energy/azimut-ha-integration/commit/111b237fbbfd1f8ed0a41a0a689e3e3588ccbeb1))

## [1.1.2](https://github.com/azimut-energy/azimut-ha-integration/compare/azimut-energy-v1.1.1...azimut-energy-v1.1.2) (2026-01-09)


### Bug Fixes

* **ci:** Fix zip structure to avoid nested azimut_energy folder ([e8dcee1](https://github.com/azimut-energy/azimut-ha-integration/commit/e8dcee190602b65566c3509b5ea1035ea70020f4))

## [1.1.1](https://github.com/azimut-energy/azimut-ha-integration/compare/azimut-energy-v1.1.0...azimut-energy-v1.1.1) (2026-01-09)


### Bug Fixes

* **ci:** Fix release asset creation by using release-please outputs ([#4](https://github.com/azimut-energy/azimut-ha-integration/issues/4)) ([fdbaab4](https://github.com/azimut-energy/azimut-ha-integration/commit/fdbaab40cd3dab522e6c8fe2d90721d784831fc0))

## [1.1.0](https://github.com/azimut-energy/azimut-ha-integration/compare/azimut-energy-v1.0.0...azimut-energy-v1.1.0) (2025-12-30)


### Features

* Add binary sensor support and enhance diagnostics in Azimut Energy integration ([681466e](https://github.com/azimut-energy/azimut-ha-integration/commit/681466e5e1fefb8de004e1dd771dcebd7329ac91))
* Add entity category handling and tests for Azimut Energy integration ([d9531ee](https://github.com/azimut-energy/azimut-ha-integration/commit/d9531ee19d85d4015f2a87e1fb365618c169c57a))
* Enhance AzimutSensor with translation key support and add sensor translations ([b885759](https://github.com/azimut-energy/azimut-ha-integration/commit/b885759781997804d92eda35838022b687931436))


### Bug Fixes

* AzimutOptionsFlow initialization in config flow ([9df873e](https://github.com/azimut-energy/azimut-ha-integration/commit/9df873ec694cf186975d1c6e4a17c36a18305c41))
* Enhance TLS context handling in AzimutMQTTClient ([75a64a8](https://github.com/azimut-energy/azimut-ha-integration/commit/75a64a89c90ee2fa7c0cc72b0d20db997a9ebbb1))


### Documentation

* Update README.md with support notice for Azimut Energy integration ([f6b4795](https://github.com/azimut-energy/azimut-ha-integration/commit/f6b4795dfb5afdf450f2bc01c75012174b3c4daf))
