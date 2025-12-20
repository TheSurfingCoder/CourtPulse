# @courtpulse/frontend

## [1.12.0](https://github.com/TheSurfingCoder/CourtPulse/compare/frontend-v1.11.0...frontend-v1.12.0) (2025-12-20)


### Features

* add public/private access tracking from OSM data ([e2b6798](https://github.com/TheSurfingCoder/CourtPulse/commit/e2b6798d35ae015f2d1c25610ebbaf67b4e15880))
* improve facility matching and court editing workflow ([bb4cda8](https://github.com/TheSurfingCoder/CourtPulse/commit/bb4cda8c5ac461f12b572f84d44a36f478614dbf))
* **sentry:** enable distributed tracing across frontend services ([87561af](https://github.com/TheSurfingCoder/CourtPulse/commit/87561af58901f9a47ab9f91de120304de355cb31))


### Bug Fixes

* merge courts from different areas instead of replacing them ([133d22b](https://github.com/TheSurfingCoder/CourtPulse/commit/133d22b4c88ea38406d2874d5bfcbdc9424de20d))

## [1.11.0](https://github.com/TheSurfingCoder/CourtPulse/compare/frontend-v1.10.0...frontend-v1.11.0) (2025-11-29)


### Features

* update map marker interactions and clustering settings ([fa480c7](https://github.com/TheSurfingCoder/CourtPulse/commit/fa480c7c185a878a4c0f91b87cb7105539cd3ab5))
* update map marker interactions and clustering settings ([12e7d82](https://github.com/TheSurfingCoder/CourtPulse/commit/12e7d82e0e760a3c11f189f480e6f8583d5eec55))

## [1.10.0](https://github.com/TheSurfingCoder/CourtPulse/compare/frontend-v1.9.0...frontend-v1.10.0) (2025-11-16)


### Features

* improve facility bbox geocoding and hybrid court updates ([6ccd759](https://github.com/TheSurfingCoder/CourtPulse/commit/6ccd7598bbbbbfe0291c68a6f952fea49fcd17cb))


### Bug Fixes

* resolve cluster name change detection bug and fix test mocks ([ec65f7c](https://github.com/TheSurfingCoder/CourtPulse/commit/ec65f7c0e8600d8a15c05d096e646f6e7dffe6be))

## [1.9.0](https://github.com/TheSurfingCoder/CourtPulse/compare/frontend-v1.8.0...frontend-v1.9.0) (2025-10-26)


### Features

* implement multi-select filters with server-driven metadata ([9df085a](https://github.com/TheSurfingCoder/CourtPulse/commit/9df085a35c6e2c6551a1b4a6872d900a3102b024))
* initialize filters with all sports and surface types selected ([dbb91a5](https://github.com/TheSurfingCoder/CourtPulse/commit/dbb91a50875f87a71da5e3246aebbd900246e1b1))


### Bug Fixes

* move console.time call after supercluster check to prevent orphan timers ([b75a3d1](https://github.com/TheSurfingCoder/CourtPulse/commit/b75a3d11679318afe494980e31b6894d2176eca9))
* require both sport and surface filters to be selected for filtering to apply ([7bb3c10](https://github.com/TheSurfingCoder/CourtPulse/commit/7bb3c10cba95afa60b5bead3b6ad54eb40a65fc0))
* update Court interface to allow null for name and cluster_group_… ([366ad90](https://github.com/TheSurfingCoder/CourtPulse/commit/366ad90a5f986deb07fdcfecc52589bc27f85cde))
* update Court interface to allow null for name and cluster_group_name ([cd047c8](https://github.com/TheSurfingCoder/CourtPulse/commit/cd047c8af045cc01ea1e8414c92af55dd5254625))

## [1.8.0](https://github.com/TheSurfingCoder/CourtPulse/compare/frontend-v1.7.0...frontend-v1.8.0) (2025-10-26)


### Features

* add dynamic metadata API endpoint for sports and surface types ([adbad9c](https://github.com/TheSurfingCoder/CourtPulse/commit/adbad9c898eb0370801c099513329ff6658855fa))
* add edit court functionality ([5a82c2b](https://github.com/TheSurfingCoder/CourtPulse/commit/5a82c2bf1c5cdf4faa114db0a768dcf33d7f38de))
* add edit court functionality ([7feb109](https://github.com/TheSurfingCoder/CourtPulse/commit/7feb1093ddbf91d6cfd3fdc09fbbdc3036f0253f))
* update cluster courts when photon_name changes; handle nulls in form ([c06cbaa](https://github.com/TheSurfingCoder/CourtPulse/commit/c06cbaa00e8c066ee5bf116e4b5e7917e626c2c5))


### Bug Fixes

* parse and use server response data after court update ([34fba77](https://github.com/TheSurfingCoder/CourtPulse/commit/34fba77513f4abd857f23a04466139513fe6ec38))
* replace handball with pickleball in sport filter ([8bf8608](https://github.com/TheSurfingCoder/CourtPulse/commit/8bf86082f43266ada1411b97dedf6173cd4d8720))
* replace handball with pickleball in sport filter ([4360ba2](https://github.com/TheSurfingCoder/CourtPulse/commit/4360ba249b320b56153ce1e7d348100702c0c0f7))
* sync surface options between EditCourtModal and FilterBar ([6768bb0](https://github.com/TheSurfingCoder/CourtPulse/commit/6768bb08d3d161c73feff6b4aee345fab5ba3214))
* update surface filter to match database ([8b55526](https://github.com/TheSurfingCoder/CourtPulse/commit/8b5552645ab19b115331741d07f7b5a98f83f448))

## [1.7.0](https://github.com/TheSurfingCoder/CourtPulse/compare/frontend-v1.6.0...frontend-v1.7.0) (2025-10-26)


### Features

* add documentation comment to main page ([efa5b08](https://github.com/TheSurfingCoder/CourtPulse/commit/efa5b08afc04631d7a505b4a119ece3d7f590043))
* add documentation comment to main page ([814ced5](https://github.com/TheSurfingCoder/CourtPulse/commit/814ced57d23082eca171584003bd310358899a34))

## [1.6.0](https://github.com/TheSurfingCoder/CourtPulse/compare/frontend-v1.5.0...frontend-v1.6.0) (2025-10-26)


### Features

* configure Release Please to run on PR creation and add Vercel ignore ([da9441e](https://github.com/TheSurfingCoder/CourtPulse/commit/da9441e440fc1d54ff56663617be5527f15e2b33))


### Bug Fixes

* update .vercelignore to remove package-lock.json exclusions ([582f73c](https://github.com/TheSurfingCoder/CourtPulse/commit/582f73ce16dfa5448abef41b1a26e8808f316161))

## [1.5.0](https://github.com/TheSurfingCoder/CourtPulse/compare/frontend-v1.4.0...frontend-v1.5.0) (2025-10-26)


### Features

* add click-to-center functionality for map clusters and courts ([993585a](https://github.com/TheSurfingCoder/CourtPulse/commit/993585a2f9ce0093ac9b1637bcbef3ceeae72b9f))
* add frontend school filter and improve public access display ([56df75d](https://github.com/TheSurfingCoder/CourtPulse/commit/56df75da98346ed97521dd2ad0375ec13061ca9d))

## [1.4.0](https://github.com/TheSurfingCoder/CourtPulse/compare/frontend-v1.3.0...frontend-v1.4.0) (2025-10-05)


### Features

* implement endpoint optimization and improve court naming ([97c64f0](https://github.com/TheSurfingCoder/CourtPulse/commit/97c64f0198d80195d7a27ce956fd9867c4a29f0a))
* implement endpoint optimization and improve court naming ([20766d4](https://github.com/TheSurfingCoder/CourtPulse/commit/20766d4b9047ae3d8440fd3fb92137ea22525f96))

## [1.3.0](https://github.com/TheSurfingCoder/CourtPulse/compare/frontend-v1.2.0...frontend-v1.3.0) (2025-10-05)


### Features

* configure Sentry for frontend and backend with environment-based setup ([b2043f8](https://github.com/TheSurfingCoder/CourtPulse/commit/b2043f88f1fd58129359aed7508eff6124c50975))
* display individual court names in popup ([d807ae6](https://github.com/TheSurfingCoder/CourtPulse/commit/d807ae6c04995fe3fc09cc6fcf9219ca22993c41))
* **root:** got sentry all set up for error monitoring ([d1a7e3a](https://github.com/TheSurfingCoder/CourtPulse/commit/d1a7e3ac9ebae7abecd4cbc7efe467d68a21fa77))

## [1.2.0](https://github.com/TheSurfingCoder/CourtPulse/compare/frontend-v1.1.1...frontend-v1.2.0) (2025-10-04)


### Features

* add comprehensive npm scripts and fix ESLint config ([b83af85](https://github.com/TheSurfingCoder/CourtPulse/commit/b83af857702766b3a91dbdc9b883f5820a3fcc54))
* add comprehensive npm scripts and fix ESLint config ([819be97](https://github.com/TheSurfingCoder/CourtPulse/commit/819be97a28d5002f9e90426f020cb0933932ba24))
* Add MapLibre GL map integration with courts data ([f34520c](https://github.com/TheSurfingCoder/CourtPulse/commit/f34520c556bf78f329a76d8d5bf52b3d88ea1fe1))
* clean up project structure and fix ESLint warnings ([b8b1e26](https://github.com/TheSurfingCoder/CourtPulse/commit/b8b1e26988f4850f0931181c2b45a24d0165aa57))
* clean up project structure and fix ESLint warnings ([df281e3](https://github.com/TheSurfingCoder/CourtPulse/commit/df281e35ab1e3fa81000679621796565a00ee758))
* complete CI pipeline setup and data pipeline fixes ([a28db90](https://github.com/TheSurfingCoder/CourtPulse/commit/a28db905e2bdbde7b3335cd3e5b0d3fae86ab6e2))
* implement coverage area caching, smart re-query detection, and clean up excessive logging ([e52ca7d](https://github.com/TheSurfingCoder/CourtPulse/commit/e52ca7d765a195d7edba1c3cac217820ce540bf9))
* optimize frontend map performance and plan viewport-based API ([cb5c920](https://github.com/TheSurfingCoder/CourtPulse/commit/cb5c92081cc3e16191afd402110a2c6ebdd2bf95))


### Bug Fixes

* Remove deploy.yml and fix migrate script to use environment NODE_ENV ([66eeda8](https://github.com/TheSurfingCoder/CourtPulse/commit/66eeda806f6332801f6d0208cc3406a0ba06d3b8))
* Remove deploy.yml and fix migrate script to use environment NODE_ENV ([ec6b89d](https://github.com/TheSurfingCoder/CourtPulse/commit/ec6b89df98ca01253b9185901ddaa19520e96751))

## 1.1.2

### Patch Changes

- [#24](https://github.com/TheSurfingCoder/CourtPulse/pull/24) [`ac7bbc8`](https://github.com/TheSurfingCoder/CourtPulse/commit/ac7bbc8f4ec58df73cc82caddd307e7ff7dd4bb1) Thanks [@TheSurfingCoder](https://github.com/TheSurfingCoder)! - fixing ci pipeline to automatically create a PR when pushing to develop branch

## 1.1.1

### Patch Changes

- [#20](https://github.com/TheSurfingCoder/CourtPulse/pull/20) [`930f5ab`](https://github.com/TheSurfingCoder/CourtPulse/commit/930f5ab35526ebdbfc7df498b1a85dcd06feb46f) Thanks [@TheSurfingCoder](https://github.com/TheSurfingCoder)! - adding fixed frontend/backend for versioning

- [#20](https://github.com/TheSurfingCoder/CourtPulse/pull/20) [`3164da5`](https://github.com/TheSurfingCoder/CourtPulse/commit/3164da5767f5d13ce2e22578b71e01c42a144096) Thanks [@TheSurfingCoder](https://github.com/TheSurfingCoder)! - Test changeset for release workflow

## 1.1.0

### Minor Changes

- Adding changesets for automated versioning and releases
