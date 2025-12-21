# Changelog

## [1.8.0](https://github.com/TheSurfingCoder/CourtPulse/compare/backend-v1.7.0...backend-v1.8.0) (2025-12-21)


### Features

* add facility_name column to courts table ([86d29f1](https://github.com/TheSurfingCoder/CourtPulse/commit/86d29f13cf8f83ea1a942eadd0b7477335d56a91))
* **sentry:** add console logging integration and environment config ([bed65c9](https://github.com/TheSurfingCoder/CourtPulse/commit/bed65c9a8c3c74e214ca0d4a7156769aa688bb5e))
* **sentry:** add console logging integration and environment config ([29cfb74](https://github.com/TheSurfingCoder/CourtPulse/commit/29cfb74764c5ef139896debce5ac45ce8113cb72))


### Bug Fixes

* add Sentry tracing headers to CORS allowedHeaders ([81e0bae](https://github.com/TheSurfingCoder/CourtPulse/commit/81e0bae22aa9ca5bc4569153c2fdcabf677b97b6))
* add Sentry tracing headers to CORS allowedHeaders ([721683f](https://github.com/TheSurfingCoder/CourtPulse/commit/721683fd22a59c15c2ae320d3b3154da263c7716))
* drop unused materialized views before removing photon_name column ([a8e1d3f](https://github.com/TheSurfingCoder/CourtPulse/commit/a8e1d3fc6d794d05be6560d7cc4f479e0edb41b1))
* drop unused materialized views before removing photon_name column ([6648fa9](https://github.com/TheSurfingCoder/CourtPulse/commit/6648fa9c87cc975812aa0346f5ba07c39f0b5067))
* make osm_courts_temp migration conditional ([e5229d7](https://github.com/TheSurfingCoder/CourtPulse/commit/e5229d71d26257d961daf89d4cbb6d14c5e438f4))
* make osm_courts_temp migration conditional ([286212c](https://github.com/TheSurfingCoder/CourtPulse/commit/286212c03ccd67bc44981620e63a772d889a0903))
* make osm_facilities migration conditional ([4a8f5d1](https://github.com/TheSurfingCoder/CourtPulse/commit/4a8f5d14270e6b372bafd39630d1cc6d5c4debc3))
* make osm_facilities migration conditional ([a4e0287](https://github.com/TheSurfingCoder/CourtPulse/commit/a4e02877589858bee6ca6b13d5ba8daaa8341d83))
* remove jest from tsconfig types after test removal ([12ab51b](https://github.com/TheSurfingCoder/CourtPulse/commit/12ab51b68d032e05781d15cdfd6c7374ccfb4d18))
* remove jest from tsconfig types after test removal ([c98bf82](https://github.com/TheSurfingCoder/CourtPulse/commit/c98bf820a0060e1dc77fc36a80f8eb400af03af0))

## [1.7.0](https://github.com/TheSurfingCoder/CourtPulse/compare/backend-v1.6.0...backend-v1.7.0) (2025-12-20)


### Features

* add public/private access tracking from OSM data ([e2b6798](https://github.com/TheSurfingCoder/CourtPulse/commit/e2b6798d35ae015f2d1c25610ebbaf67b4e15880))
* improve facility matching and court editing workflow ([bb4cda8](https://github.com/TheSurfingCoder/CourtPulse/commit/bb4cda8c5ac461f12b572f84d44a36f478614dbf))
* **sentry:** enable distributed tracing across frontend services ([87561af](https://github.com/TheSurfingCoder/CourtPulse/commit/87561af58901f9a47ab9f91de120304de355cb31))
* switch cluster_group_name mapping from photon_name to facility_name ([31c9bb9](https://github.com/TheSurfingCoder/CourtPulse/commit/31c9bb983917726b8f3c4b779d6f317269d9a164))


### Bug Fixes

* merge courts from different areas instead of replacing them ([133d22b](https://github.com/TheSurfingCoder/CourtPulse/commit/133d22b4c88ea38406d2874d5bfcbdc9424de20d))
* resolve enriched_name column and UnboundLocalError bugs ([563f79f](https://github.com/TheSurfingCoder/CourtPulse/commit/563f79f73d7bee20641838a436403bfea32518ad))

## [1.6.0](https://github.com/TheSurfingCoder/CourtPulse/compare/backend-v1.5.0...backend-v1.6.0) (2025-11-16)


### Features

* improve facility bbox geocoding and hybrid court updates ([6ccd759](https://github.com/TheSurfingCoder/CourtPulse/commit/6ccd7598bbbbbfe0291c68a6f952fea49fcd17cb))
* improve facility bbox geocoding and hybrid court updates ([65aaa35](https://github.com/TheSurfingCoder/CourtPulse/commit/65aaa354e637463e328cd2621412058a1fea97d5))
* remove unused columns and update data mapping logic ([b21d879](https://github.com/TheSurfingCoder/CourtPulse/commit/b21d879800392af60a901a8e463c6633c8c07fb5))


### Bug Fixes

* resolve cluster name change detection bug and fix test mocks ([ec65f7c](https://github.com/TheSurfingCoder/CourtPulse/commit/ec65f7c0e8600d8a15c05d096e646f6e7dffe6be))

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
