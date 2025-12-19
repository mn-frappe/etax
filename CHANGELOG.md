## [1.5.0](https://github.com/mn-frappe/etax/compare/v1.4.0...v1.5.0) (2025-12-19)

### 🚀 Features

* Add ERPNext VAT integration hooks and eTax Invoice Link doctype ([#8](https://github.com/mn-frappe/etax/issues/8)) ([8ff6370](https://github.com/mn-frappe/etax/commit/8ff6370a1af602b29c3811d73da880f4b3ee40d1))

## [1.4.0](https://github.com/mn-frappe/etax/compare/v1.3.0...v1.4.0) (2025-12-17)

### 🚀 Features

* add CodeQL, CODEOWNERS, MkDocs documentation ([3aafced](https://github.com/mn-frappe/etax/commit/3aafcedad1c51bc44dd1d3e03584f405b658b479))
* add mypy type checking, matrix testing, enhanced VS Code ([35dfa96](https://github.com/mn-frappe/etax/commit/35dfa9629ccbea548aa14c5d5f8b4d65237482de))
* add semantic-release for automatic versioning ([d92e6a4](https://github.com/mn-frappe/etax/commit/d92e6a401b8537e3ef932c3262c79cd5d11dcf3d))
* add telemetry for GitHub issue auto-creation ([6de7ea0](https://github.com/mn-frappe/etax/commit/6de7ea0fc445c55bb566c767879c994d9048b993))

### 🐛 Bug Fixes

* resolve type errors in telemetry module ([ab51038](https://github.com/mn-frappe/etax/commit/ab510389cc8743ef47224dc40351b095b60733b3))
* semantic-release auth and missing npm package ([4539b81](https://github.com/mn-frappe/etax/commit/4539b81810d4287abbe8bea57e29160725241d83))

# Changelog

All notable changes to eTax will be documented in this file.

## [1.3.0] - 2024-12-17

### Added
- Multi-company entity support
- Test Connection button in settings
- Comprehensive test suite (54 tests)
- Enhanced ERPNext app compatibility

### Changed
- All sections collapsible by default
- Improved workspace layout

### Fixed
- Duplicate pyproject.toml sections
- Fixed CI linting errors

## [1.2.0] - 2024-12-17

### Added
- Multi-company entity support
- Enhanced ERPNext app compatibility
- Local mn_entity.py for CI compatibility

## [1.1.1] - 2024-12-16

### Added
- 100% MTA API coverage
- Performance optimizations
- Response caching
- Error handling improvements

### Changed
- Improved API error handling
- Better field descriptions

## [1.1.0] - 2024-12-16

### Added
- Mongolian field descriptions
- Collapsible sections
- eTax workspace integration
- i18n support with Mongolian translations

## [1.0.0] - 2024-12-16

### Added
- Initial release
- MTA eTax API integration
- TIN validation and verification
- Tax statement generation
- VAT declaration integration
- Tax payment tracking
