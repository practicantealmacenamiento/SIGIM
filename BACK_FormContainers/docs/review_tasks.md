# Review Findings - Pending Work

## 1. Typographical error in deployment command notes
- **Location:** `command.md`, line 3.
- **Issue:** The comment reads "Subimos los el contenedro", which contains duplicated article usage and a misspelling of "contenedor".
- **Impact:** Reduces clarity for operators following the documented deployment steps.
- **Proposed task:** Update the comment to proper Spanish (e.g., "Subimos el contenedor") to eliminate the typo.

## 2. Missing precinto rules module breaks OCR flows
- **Location:** Tests such as `app/tests/test_precinto_detection.py` import `app.domain.precinto_rules`, but the module is absent under `app/domain/`.
- **Evidence:** Running `pytest -q` raises `ModuleNotFoundError: No module named 'app.domain.precinto_rules'` during collection.
- **Impact:** OCR-related functionality and the associated command `test_precinto_rules` cannot run, blocking regression coverage for precinto detection.
- **Proposed task:** Restore or reimplement `app/domain/precinto_rules.py` (and any related services) so the tests and commands compile again.

## 3. Documentation references nonexistent modules
- **Location:** `docs/mejoras_implementadas.md`, lines 45-102.
- **Issue:** The document states that files like `app/domain/precinto_rules.py` and `app/application/verification_enhanced.py` were created, but these files do not exist in the repository.
- **Impact:** Contributors are misled about available components and may spend time searching for missing implementations.
- **Proposed task:** Update the documentation to reflect the current codebase or reintroduce the referenced modules so docs and code stay in sync.

## 4. Strengthen gerencia API test coverage
- **Location:** `app/tests/test_gerencia.py`.
- **Issue:** The test only asserts a `200 OK` status on `/app/api/gerencias/` without seeding data or validating the response body, and it currently fails early because Django settings are not configured when `APIClient` is instantiated.
- **Impact:** The test cannot run successfully under `pytest` and provides minimal coverage of the endpoint behaviour.
- **Proposed task:** Convert the test into a proper Django/pytest test that loads fixtures or factories, verifies the payload, and runs under a configured Django settings module (e.g., by ensuring `pytest-django` is available or by using Django's test client inside a `TestCase`).
