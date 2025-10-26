# Changelog

## [1.5.0](https://github.com/TheSurfingCoder/CourtPulse/compare/backend-v1.4.0...backend-v1.5.0) (2025-10-26)


### Features

* add dynamic metadata API endpoint for sports and surface types ([adbad9c](https://github.com/TheSurfingCoder/CourtPulse/commit/adbad9c898eb0370801c099513329ff6658855fa))
* add edit court functionality ([5a82c2b](https://github.com/TheSurfingCoder/CourtPulse/commit/5a82c2bf1c5cdf4faa114db0a768dcf33d7f38de))
* add edit court functionality ([7feb109](https://github.com/TheSurfingCoder/CourtPulse/commit/7feb1093ddbf91d6cfd3fdc09fbbdc3036f0253f))
* update cluster courts when photon_name changes; handle nulls in form ([c06cbaa](https://github.com/TheSurfingCoder/CourtPulse/commit/c06cbaa00e8c066ee5bf116e4b5e7917e626c2c5))

## [1.4.0](https://github.com/TheSurfingCoder/CourtPulse/compare/backend-v1.3.0...backend-v1.4.0) (2025-10-26)


### Features

* add click-to-center functionality for map clusters and courts ([993585a](https://github.com/TheSurfingCoder/CourtPulse/commit/993585a2f9ce0093ac9b1637bcbef3ceeae72b9f))
* consolidate to production-only infrastructure ([d52318d](https://github.com/TheSurfingCoder/CourtPulse/commit/d52318d0d56d2eae87b39731dce34e320d74f2c9))
* consolidate to production-only infrastructure ([f7f97b2](https://github.com/TheSurfingCoder/CourtPulse/commit/f7f97b2ae2cc7897648665a35774a70361ed1516))
* implement bounding box geocoding with hash-based clustering ([0b5a54a](https://github.com/TheSurfingCoder/CourtPulse/commit/0b5a54a57488fc46c465fd1c0517e423163f25cc))
* implement bounding box geocoding with hash-based clustering ([a4985e8](https://github.com/TheSurfingCoder/CourtPulse/commit/a4985e8a12512f1a492ce9cdbaef3d16b905d5de))

## [1.3.0](https://github.com/TheSurfingCoder/CourtPulse/compare/backend-v1.2.0...backend-v1.3.0) (2025-10-05)


### Features

* implement endpoint optimization and improve court naming ([97c64f0](https://github.com/TheSurfingCoder/CourtPulse/commit/97c64f0198d80195d7a27ce956fd9867c4a29f0a))
* implement endpoint optimization and improve court naming ([20766d4](https://github.com/TheSurfingCoder/CourtPulse/commit/20766d4b9047ae3d8440fd3fb92137ea22525f96))

## [1.2.0](https://github.com/TheSurfingCoder/CourtPulse/compare/backend-v1.1.0...backend-v1.2.0) (2025-10-05)


### Features

* configure Sentry for frontend and backend with environment-based setup ([b2043f8](https://github.com/TheSurfingCoder/CourtPulse/commit/b2043f88f1fd58129359aed7508eff6124c50975))
* improve court display and clean up git tracking ([1fd9ad7](https://github.com/TheSurfingCoder/CourtPulse/commit/1fd9ad744846a57dbd629a4a0b3ec7bcbac4b682))
* **root:** got sentry all set up for error monitoring ([d1a7e3a](https://github.com/TheSurfingCoder/CourtPulse/commit/d1a7e3ac9ebae7abecd4cbc7efe467d68a21fa77))


### Bug Fixes

* fixed issues with prod database ([a82c2f4](https://github.com/TheSurfingCoder/CourtPulse/commit/a82c2f4c1cf3d5b6b0625928b3909967bc6e3d9f))
* fixed issues with prod database ([064f1b1](https://github.com/TheSurfingCoder/CourtPulse/commit/064f1b19eb275bca0c7eb243ed4960b1d7274015))
* **pipeline:** made schools top priority in pipeline ([0804a37](https://github.com/TheSurfingCoder/CourtPulse/commit/0804a3732c0e3cd35daf8a2945915f2d1cb699b2))
* remove runMigrations function to avoid conflict with pre-deploy command ([594aa8b](https://github.com/TheSurfingCoder/CourtPulse/commit/594aa8b9f07cf4655805671a1b15fa1384435722))

## [1.1.0](https://github.com/TheSurfingCoder/CourtPulse/compare/backend-v1.0.1...backend-v1.1.0) (2025-10-04)


### Features

* add comprehensive npm scripts and fix ESLint config ([b83af85](https://github.com/TheSurfingCoder/CourtPulse/commit/b83af857702766b3a91dbdc9b883f5820a3fcc54))
* add comprehensive npm scripts and fix ESLint config ([819be97](https://github.com/TheSurfingCoder/CourtPulse/commit/819be97a28d5002f9e90426f020cb0933932ba24))
* add data enrichment pipeline and database migration ([3b0cf57](https://github.com/TheSurfingCoder/CourtPulse/commit/3b0cf57c848ae1f8d168834116d709e2f1ee42a3))
* add data enrichment pipeline and database migration ([ccb72fb](https://github.com/TheSurfingCoder/CourtPulse/commit/ccb72fbdd7726991d119f9d1f13025c0c136cad6))
* complete CI pipeline setup and data pipeline fixes ([a28db90](https://github.com/TheSurfingCoder/CourtPulse/commit/a28db905e2bdbde7b3335cd3e5b0d3fae86ab6e2))
* Complete data enrichment pipeline and cleanup ([be4279d](https://github.com/TheSurfingCoder/CourtPulse/commit/be4279d55c5dcc0d58a538161ab434b0e3bbd300))
* Complete data enrichment pipeline and cleanup ([9d28d38](https://github.com/TheSurfingCoder/CourtPulse/commit/9d28d38fda4f08726e9bd16292e8e79fb867c650))
* complete data pipeline with Point/Polygon support and coordinate normalization ([c6fe9a6](https://github.com/TheSurfingCoder/CourtPulse/commit/c6fe9a6f353e3a6d0f40938eecea57633ab6d52f))
* enhance data pipeline with manual-only workflow and improved backup/rollback ([846be4b](https://github.com/TheSurfingCoder/CourtPulse/commit/846be4bffa73f3e0284d26cb4101d411202d01ac))
* implement coverage area caching, smart re-query detection, and clean up excessive logging ([e52ca7d](https://github.com/TheSurfingCoder/CourtPulse/commit/e52ca7d765a195d7edba1c3cac217820ce540bf9))
* implement professional migration system with node-pg-migrate ([eb118c0](https://github.com/TheSurfingCoder/CourtPulse/commit/eb118c09db74c21fe3e1b2ff02eeb45a380095be))
* implement professional migration system with node-pg-migrate ([73c123e](https://github.com/TheSurfingCoder/CourtPulse/commit/73c123e2f825a6619bb438da752ded072df7ae84))
* make pipeline completely sequential to avoid API rate limiting ([47df864](https://github.com/TheSurfingCoder/CourtPulse/commit/47df86459cf223285c1925ec9a4a4bfe38c2246c))
* optimize frontend map performance and plan viewport-based API ([cb5c920](https://github.com/TheSurfingCoder/CourtPulse/commit/cb5c92081cc3e16191afd402110a2c6ebdd2bf95))


### Bug Fixes

* Add CORS support for Vercel staging domain ([f452811](https://github.com/TheSurfingCoder/CourtPulse/commit/f4528115ac43de4d74cc10d441bf2763e0886be2))
* Add PostGIS extension to migration ([6cc35b3](https://github.com/TheSurfingCoder/CourtPulse/commit/6cc35b36d826198f4dc1c0286c9a4797ba002d01))
* Create missing initial migration and fix Court model ([ec82936](https://github.com/TheSurfingCoder/CourtPulse/commit/ec82936ba90e46e1e7715a1ca8d34625d2a54d74))
* Improve ENUM conversion in migration ([cf9e7d1](https://github.com/TheSurfingCoder/CourtPulse/commit/cf9e7d1dce5265f9b567d03fb1e9e7574a2b28ab))
* Remove deploy.yml and fix migrate script to use environment NODE_ENV ([66eeda8](https://github.com/TheSurfingCoder/CourtPulse/commit/66eeda806f6332801f6d0208cc3406a0ba06d3b8))
* Remove deploy.yml and fix migrate script to use environment NODE_ENV ([ec6b89d](https://github.com/TheSurfingCoder/CourtPulse/commit/ec6b89df98ca01253b9185901ddaa19520e96751))
* remove dist files from git and add to .gitignore ([3cae0a2](https://github.com/TheSurfingCoder/CourtPulse/commit/3cae0a27424906885b89c2910c4db46a9e53df97))
* resolve node-pg-migrate ordering issue ([d061976](https://github.com/TheSurfingCoder/CourtPulse/commit/d061976643fcc672cb210b7330a495caf7006c5a))
* Resolve TypeScript compilation errors in Court model ([85773db](https://github.com/TheSurfingCoder/CourtPulse/commit/85773dbf83cb68e025ac6c3c1162091ec22ebca0))
* Simplify CORS configuration and add debugging ([c1e9e06](https://github.com/TheSurfingCoder/CourtPulse/commit/c1e9e06d646d94d0be3a9acda0f9c13637e97a67))
* Update Court model to match new database schema ([e587f11](https://github.com/TheSurfingCoder/CourtPulse/commit/e587f11a9fd38f709435fc9d29da0ecf5ced90a2))
* Update Court model to match new database schema ([3fcfe43](https://github.com/TheSurfingCoder/CourtPulse/commit/3fcfe43c21d546a3ea6cac07f9769e95bf96237b))

## [1.1.0](https://github.com/TheSurfingCoder/CourtPulse/compare/backend-v1.0.1...backend-v1.1.0) (2025-10-04)


### Features

* add comprehensive npm scripts and fix ESLint config ([b83af85](https://github.com/TheSurfingCoder/CourtPulse/commit/b83af857702766b3a91dbdc9b883f5820a3fcc54))
* add comprehensive npm scripts and fix ESLint config ([819be97](https://github.com/TheSurfingCoder/CourtPulse/commit/819be97a28d5002f9e90426f020cb0933932ba24))
* add data enrichment pipeline and database migration ([3b0cf57](https://github.com/TheSurfingCoder/CourtPulse/commit/3b0cf57c848ae1f8d168834116d709e2f1ee42a3))
* add data enrichment pipeline and database migration ([ccb72fb](https://github.com/TheSurfingCoder/CourtPulse/commit/ccb72fbdd7726991d119f9d1f13025c0c136cad6))
* complete CI pipeline setup and data pipeline fixes ([a28db90](https://github.com/TheSurfingCoder/CourtPulse/commit/a28db905e2bdbde7b3335cd3e5b0d3fae86ab6e2))
* Complete data enrichment pipeline and cleanup ([be4279d](https://github.com/TheSurfingCoder/CourtPulse/commit/be4279d55c5dcc0d58a538161ab434b0e3bbd300))
* Complete data enrichment pipeline and cleanup ([9d28d38](https://github.com/TheSurfingCoder/CourtPulse/commit/9d28d38fda4f08726e9bd16292e8e79fb867c650))
* complete data pipeline with Point/Polygon support and coordinate normalization ([c6fe9a6](https://github.com/TheSurfingCoder/CourtPulse/commit/c6fe9a6f353e3a6d0f40938eecea57633ab6d52f))
* enhance data pipeline with manual-only workflow and improved backup/rollback ([846be4b](https://github.com/TheSurfingCoder/CourtPulse/commit/846be4bffa73f3e0284d26cb4101d411202d01ac))
* implement coverage area caching, smart re-query detection, and clean up excessive logging ([e52ca7d](https://github.com/TheSurfingCoder/CourtPulse/commit/e52ca7d765a195d7edba1c3cac217820ce540bf9))
* implement professional migration system with node-pg-migrate ([eb118c0](https://github.com/TheSurfingCoder/CourtPulse/commit/eb118c09db74c21fe3e1b2ff02eeb45a380095be))
* implement professional migration system with node-pg-migrate ([73c123e](https://github.com/TheSurfingCoder/CourtPulse/commit/73c123e2f825a6619bb438da752ded072df7ae84))
* make pipeline completely sequential to avoid API rate limiting ([47df864](https://github.com/TheSurfingCoder/CourtPulse/commit/47df86459cf223285c1925ec9a4a4bfe38c2246c))
* optimize frontend map performance and plan viewport-based API ([cb5c920](https://github.com/TheSurfingCoder/CourtPulse/commit/cb5c92081cc3e16191afd402110a2c6ebdd2bf95))


### Bug Fixes

* Add CORS support for Vercel staging domain ([f452811](https://github.com/TheSurfingCoder/CourtPulse/commit/f4528115ac43de4d74cc10d441bf2763e0886be2))
* Add PostGIS extension to migration ([6cc35b3](https://github.com/TheSurfingCoder/CourtPulse/commit/6cc35b36d826198f4dc1c0286c9a4797ba002d01))
* Create missing initial migration and fix Court model ([ec82936](https://github.com/TheSurfingCoder/CourtPulse/commit/ec82936ba90e46e1e7715a1ca8d34625d2a54d74))
* Improve ENUM conversion in migration ([cf9e7d1](https://github.com/TheSurfingCoder/CourtPulse/commit/cf9e7d1dce5265f9b567d03fb1e9e7574a2b28ab))
* Remove deploy.yml and fix migrate script to use environment NODE_ENV ([66eeda8](https://github.com/TheSurfingCoder/CourtPulse/commit/66eeda806f6332801f6d0208cc3406a0ba06d3b8))
* Remove deploy.yml and fix migrate script to use environment NODE_ENV ([ec6b89d](https://github.com/TheSurfingCoder/CourtPulse/commit/ec6b89df98ca01253b9185901ddaa19520e96751))
* remove dist files from git and add to .gitignore ([3cae0a2](https://github.com/TheSurfingCoder/CourtPulse/commit/3cae0a27424906885b89c2910c4db46a9e53df97))
* resolve node-pg-migrate ordering issue ([d061976](https://github.com/TheSurfingCoder/CourtPulse/commit/d061976643fcc672cb210b7330a495caf7006c5a))
* Resolve TypeScript compilation errors in Court model ([85773db](https://github.com/TheSurfingCoder/CourtPulse/commit/85773dbf83cb68e025ac6c3c1162091ec22ebca0))
* Simplify CORS configuration and add debugging ([c1e9e06](https://github.com/TheSurfingCoder/CourtPulse/commit/c1e9e06d646d94d0be3a9acda0f9c13637e97a67))
* Update Court model to match new database schema ([e587f11](https://github.com/TheSurfingCoder/CourtPulse/commit/e587f11a9fd38f709435fc9d29da0ecf5ced90a2))
* Update Court model to match new database schema ([3fcfe43](https://github.com/TheSurfingCoder/CourtPulse/commit/3fcfe43c21d546a3ea6cac07f9769e95bf96237b))
