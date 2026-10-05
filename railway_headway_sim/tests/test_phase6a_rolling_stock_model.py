"""Phase-6A acceptance tests: the typed rolling-stock catalogue (TEST P6-001 … P6-024).

Stage 6A declares what a rolling-stock object *is*: the typed model, the reader for
the four accepted source forms, the ``GRR-01`` rolling-stock companion file and the
physical-validity rules. Nothing here exercises motion: no trajectory, no speed
envelope, no acceleration, no integration, no time step — and the delivered modules
import the physics package nowhere.

Conventions of this suite (identical to the Phase-5A/5B suites):

* the frozen reference values are read from the delivered companion file (and from
  the loaded typed instance); the test recomputes derived quantities from the
  instance instead of re-typing them, and pins the file itself by SHA-256;
* every rule is proven by a *reported* diagnostic via the project's existing
  ``ValidationResult`` / ``Diagnostic`` model, never by behaviour inside the library;
* the Section-D scan and the import-surface scan run against the delivered modules,
  with the scan surface itself asserted (S1 9 tokens, S3 7 tokens, the same five
  allowed tokens).
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import inspect
import json
import re
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_DIR = _REPO_ROOT / "railway_headway_sim"
_MODEL_MODULE_PATH = _PACKAGE_DIR / "models" / "rolling_stock.py"
_VALIDATION_MODULE_PATH = _PACKAGE_DIR / "validation" / "rolling_stock_validation.py"
_COMPANION_PATH = _REPO_ROOT / "examples" / "GRR-01-rolling-stock.json"
_GRR01_PATH = _REPO_ROOT / "examples" / "GRR-01.json"
_PATHS_COMPANION_PATH = _REPO_ROOT / "examples" / "GRR-01-paths.json"
_SECTION_D_PATH = _REPO_ROOT / "docs" / "SECTION_D_PATTERNS.md"

#: sha256 of the delivered rolling-stock companion file. The frozen reference values
#: of §D4 live in that file (and are quoted in the run report), so pinning the file's
#: hash pins every one of them without re-typing the numbers in this test.
COMPANION_SHA256 = "6b03e36f4f4959ab343019eea918160f8e019ebb56a50207a7fc577cbb50c93d"

#: Protected artefacts of the frozen project (must not change in Phase 6A).
GRR01_SHA256 = "ad0a26265d4e072aeedcc69161bef90f200c20b4efb12a4d56a5276c4a4f7a56"
PATHS_COMPANION_SHA256 = "c62c3ee6d910457a6f59533c2b92b4e65a0cd8c64dff49fe8e6796ed829fac86"
CANONICAL_GRR01_HASH = "5189aaa2340c17022666ef44772c7d34f99b2fea9ee9609bb7b7513238ef4dbe"

#: Module names the delivered modules must not import from. Composed here so that this
#: file never carries the literal module path of a delivered module (the Phase-4B
#: importer scan reads every package file as text).
_FORBIDDEN_IMPORT_TARGETS = (
    "compiled" + "_network",
    "geometry_" + "along_route",
    "resistance",
    "along_route",
)

#: Libraries the delivered modules must not import (the Phase-4B/5A/5B list).
_NUMERIC_LIBRARIES = (
    "math",
    "numpy",
    "scipy",
    "pandas",
    "statistics",
    "random",
    "decimal",
    "fractions",
)

#: The documented model surface of §D1 (top-level catalogue and one stock object).
CATALOGUE_FIELDS = (
    "schema_version",
    "document_kind",
    "project_id",
    "project_file",
    "project_file_sha256",
    "project_canonical_hash",
    "notes",
    "rolling_stock",
)
STOCK_FIELDS = (
    "id",
    "name",
    "category",
    "data_status",
    "manufacturer_data",
    "geometry",
    "mass",
    "performance_limits",
    "traction",
    "running_resistance",
    "curve_resistance",
    "service_braking",
    "etcs_supervision",
)
PROPERTY_NAMES = (
    "mass_kg",
    "length_m",
    "effective_mass_kg",
    "max_speed_kmh",
    "resistance_a_kn",
    "resistance_b_kn_per_kmh",
    "resistance_c_kn_per_kmh2",
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _model_module():
    """Return the delivered rolling-stock model module."""
    return importlib.import_module("railway_headway_sim.models.rolling_stock")


def _validation_module():
    """Return the delivered rolling-stock validation module."""
    return importlib.import_module("railway_headway_sim.validation.rolling_stock_validation")


def _codes():
    """Return the diagnostic code catalogue."""
    from railway_headway_sim.validation import codes

    return codes


def _raw_document() -> dict[str, Any]:
    """Return the delivered companion file as plain data (no model involved)."""
    return json.loads(_COMPANION_PATH.read_text(encoding="utf-8"))


def _catalogue():
    """Return the typed catalogue loaded through the delivered reader."""
    return _model_module().load_rolling_stock_catalogue(_COMPANION_PATH)


def _raw_stock(document: dict[str, Any], stock_id: str) -> dict[str, Any]:
    """Return the raw mapping of one stock type of the companion document."""
    entries = [entry for entry in document["rolling_stock"] if entry["id"] == stock_id]
    assert len(entries) == 1, f"{stock_id} must appear exactly once in the companion file"
    return entries[0]


def _typed_stock(stock_id: str):
    """Return the typed stock object of one stock type."""
    matches = [stock for stock in _catalogue().rolling_stock if stock.id == stock_id]
    assert len(matches) == 1, stock_id
    return matches[0]


def _copy(stock):
    """Return a deep, independently mutable copy of one typed stock object."""
    return stock.model_copy(deep=True)


def _codes_of(diagnostics: list[Any]) -> list[str]:
    """Return the codes of *diagnostics*, in order."""
    return [diagnostic.code for diagnostic in diagnostics]


def _fields_of(diagnostics: list[Any]) -> list[str]:
    """Return the named field of every diagnostic (context and message checked)."""
    fields: list[str] = []
    for diagnostic in diagnostics:
        field = (diagnostic.context or {}).get("field")
        assert field, f"diagnostic {diagnostic.code} does not name its field"
        leaf = field.rsplit(".", 1)[-1]
        assert field in diagnostic.message or leaf in diagnostic.message, (
            f"diagnostic {diagnostic.code} does not name '{field}' in its message"
        )
        fields.append(str(field))
    return fields


def _canonical_json(catalogue) -> str:
    """Return the canonical JSON text of a catalogue (the project's canonicalisation)."""
    from railway_headway_sim.io.project_io import canonical_json_text

    return canonical_json_text(catalogue.model_dump(mode="json"))


def _section_tokens(heading: str) -> tuple[str, ...]:
    """Return the token list of one ``docs/SECTION_D_PATTERNS.md`` section."""
    text = _SECTION_D_PATH.read_text(encoding="utf-8")
    start = text.index(heading)
    end = text.index("\n## ", start + 1)
    body = text[start:end].split("\n", 1)[1]
    paragraph = body.strip().split("\n\n", 1)[0]
    return tuple(re.findall(r"`([^`]+)`", paragraph))


def _declared_names(path: Path) -> list[str]:
    """Return every declared function / async function / class name of one module."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]


def _import_edges(path: Path) -> set[str]:
    """Return the import surface of one module file, in the P4-046 notation."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add("." * node.level + (node.module or ""))
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    return imported


def _assert_carries(raw: Any, dumped: Any, path: str) -> None:
    """Assert every value of *raw* appears unchanged in *dumped* (dumped may add keys)."""
    if isinstance(raw, dict):
        assert isinstance(dumped, dict), (path, type(dumped).__name__)
        for key, value in raw.items():
            assert key in dumped, f"{path}.{key} is missing from the typed model"
            _assert_carries(value, dumped[key], f"{path}.{key}")
    else:
        assert dumped == raw, (path, dumped, raw)


def _sha256(path: Path) -> str:
    """Return the SHA-256 of a file on disk."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# TEST P6-001
# ---------------------------------------------------------------------------
def test_p6_001_model_module_exists_and_exposes_the_documented_surface():
    """TEST P6-001 - the module exists, imports cleanly, and exposes the documented API."""
    from railway_headway_sim.models.diagnostics import ValidationResult

    assert _MODEL_MODULE_PATH.is_file(), "models/rolling_stock.py must exist"
    assert _VALIDATION_MODULE_PATH.is_file(), "validation/rolling_stock_validation.py must exist"
    module = _model_module()  # importing it must be side-effect free
    for name in (
        "RollingStockCatalogue",
        "RollingStock",
        "RollingStockError",
        "RollingStockCategory",
        "TractiveEffortModel",
        "RunningResistanceModel",
        "BrakingModel",
        "load_rolling_stock_catalogue",
    ):
        assert hasattr(module, name), name
        assert name in module.__all__, name
    assert module.ROLLING_STOCK_DOCUMENT_KIND == "ROLLING_STOCK_CATALOGUE"

    parameters = list(inspect.signature(module.load_rolling_stock_catalogue).parameters.values())
    assert [parameter.name for parameter in parameters] == ["source"], parameters
    assert all(parameter.default is inspect.Parameter.empty for parameter in parameters), (
        "the reader takes exactly one required positional argument"
    )
    assert issubclass(module.RollingStockError, ValueError)

    assert tuple(module.RollingStockCatalogue.model_fields) == CATALOGUE_FIELDS
    assert tuple(module.RollingStock.model_fields) == STOCK_FIELDS
    assert [member.value for member in module.RollingStockCategory] == [
        "HIGH_SPEED_PASSENGER",
        "REGIONAL_PASSENGER",
    ]
    assert [member.value for member in module.TractiveEffortModel] == [
        "FORCE_THEN_POWER_LIMITED"
    ]
    assert [member.value for member in module.RunningResistanceModel] == ["DAVIS"]
    assert [member.value for member in module.BrakingModel] == [
        "CONSTANT_EQUIVALENT_BRAKE_FORCE"
    ]

    # the read-only convenience properties of §D2 exist and are properties (not fields)
    for name in PROPERTY_NAMES:
        attribute = inspect.getattr_static(module.RollingStock, name)
        assert isinstance(attribute, property), name
        assert name not in module.RollingStock.model_fields, f"{name} must not be a stored field"

    validator = _validation_module()
    for name in ("validate_rolling_stock_catalogue", "validate_rolling_stock"):
        assert hasattr(validator, name), name
    empty = module.RollingStockCatalogue.model_construct(rolling_stock=[])
    result = validator.validate_rolling_stock_catalogue(empty)
    assert isinstance(result, ValidationResult)
    assert result.status.value == "VALID"
    assert validator.validate_rolling_stock(_typed_stock("RS-HSR320")) == []


# ---------------------------------------------------------------------------
# TEST P6-002
# ---------------------------------------------------------------------------
def test_p6_002_companion_file_loads_and_validates_with_no_diagnostic():
    """TEST P6-002 - the companion file exists, loads, and validates with zero diagnostics."""
    assert _COMPANION_PATH.is_file(), "examples/GRR-01-rolling-stock.json must exist"
    assert _sha256(_COMPANION_PATH) == COMPANION_SHA256, "the companion file changed"
    catalogue = _catalogue()
    result = _validation_module().validate_rolling_stock_catalogue(catalogue)
    assert result.diagnostics == [], [d.format_line() for d in result.diagnostics]
    assert result.error_count == 0 and result.warning_count == 0 and result.info_count == 0
    assert result.status.value == "VALID"
    assert catalogue.document_kind == "ROLLING_STOCK_CATALOGUE"
    assert catalogue.schema_version == "1.0"
    assert catalogue.project_file == "examples/GRR-01.json"
    assert catalogue.project_file_sha256 == GRR01_SHA256
    assert catalogue.project_canonical_hash == CANONICAL_GRR01_HASH
    assert catalogue.notes and all(isinstance(note, str) for note in catalogue.notes)


# ---------------------------------------------------------------------------
# TEST P6-003
# ---------------------------------------------------------------------------
def test_p6_003_companion_declares_exactly_the_two_reference_stock_types():
    """TEST P6-003 - the companion file declares exactly RS-HSR320 and RS-REG200."""
    document = _raw_document()
    assert document["document_kind"] == "ROLLING_STOCK_CATALOGUE"
    raw_ids = [entry["id"] for entry in document["rolling_stock"]]
    assert sorted(raw_ids) == ["RS-HSR320", "RS-REG200"], raw_ids
    assert len(raw_ids) == 2
    catalogue = _catalogue()
    assert sorted(stock.id for stock in catalogue.rolling_stock) == sorted(raw_ids)
    assert [stock.category.value for stock in catalogue.rolling_stock] == [
        "HIGH_SPEED_PASSENGER",
        "REGIONAL_PASSENGER",
    ]
    assert [stock.data_status for stock in catalogue.rolling_stock] == [
        "REFERENCE_ASSUMPTION",
        "SYNTHETIC_REFERENCE",
    ]
    assert all(stock.manufacturer_data is False for stock in catalogue.rolling_stock)
    assert all(stock.name and isinstance(stock.name, str) for stock in catalogue.rolling_stock)


# ---------------------------------------------------------------------------
# TEST P6-004 / TEST P6-005
# ---------------------------------------------------------------------------
def _assert_stock_matches_the_file(stock_id: str) -> Any:
    """Assert the typed instance carries exactly the values the companion file stores."""
    raw = _raw_stock(_raw_document(), stock_id)
    stock = _typed_stock(stock_id)
    dumped = stock.model_dump(mode="json")
    _assert_carries(raw, dumped, stock_id)

    # the only key the typed model adds is the documented optional characteristic
    assert set(dumped["traction"]) - set(raw["traction"]) == {"traction_curve"}, (
        set(dumped["traction"]) - set(raw["traction"])
    )
    assert dumped["traction"]["traction_curve"] is None
    assert set(dumped) - set(raw) == set()

    # derived quantities recomputed from the loaded instance (never re-typed here)
    assert stock.mass_kg == float(stock.mass.static_mass_t) * 1000.0
    assert stock.effective_mass_kg == (
        float(stock.mass.static_mass_t) * 1000.0 * float(stock.mass.rotating_mass_factor)
    )
    assert stock.length_m == float(stock.geometry.length_m)
    assert stock.max_speed_kmh == float(stock.performance_limits.max_speed_kmh)
    assert stock.resistance_a_kn == float(stock.running_resistance.coefficients.A)
    assert stock.resistance_b_kn_per_kmh == float(stock.running_resistance.coefficients.B)
    assert stock.resistance_c_kn_per_kmh2 == float(stock.running_resistance.coefficients.C)
    # the physical floors of §D4, recomputed from the instance
    assert stock.mass.static_mass_t > 0 and stock.geometry.length_m > 0
    assert stock.mass.rotating_mass_factor >= 1.0
    assert stock.performance_limits.max_speed_kmh > 0
    assert stock.performance_limits.max_operational_acceleration_mps2 > 0
    assert stock.traction.rated_power_kw > 0
    assert stock.traction.max_tractive_effort_kn > 0
    assert stock.running_resistance.coefficients.A >= 0
    assert stock.running_resistance.coefficients.B >= 0
    assert stock.running_resistance.coefficients.C >= 0
    assert stock.service_braking.reference_deceleration_mps2 > 0
    assert stock.etcs_supervision.reference_deceleration_mps2 > 0
    assert stock.traction.traction_curve is None
    return stock


def test_p6_004_hsr_stock_carries_the_frozen_reference_values():
    """TEST P6-004 - the typed RS-HSR320 instance carries the frozen HSR values."""
    stock = _assert_stock_matches_the_file("RS-HSR320")
    assert stock.category.value == "HIGH_SPEED_PASSENGER"
    assert stock.data_status == "REFERENCE_ASSUMPTION"
    assert stock.running_resistance.model.value == "DAVIS"
    assert stock.running_resistance.formula == "A_PLUS_BV_PLUS_CV2"
    assert stock.running_resistance.coefficient_speed_unit == "km/h"
    assert stock.running_resistance.output_force_unit == "kN"
    assert stock.traction.model.value == "FORCE_THEN_POWER_LIMITED"
    assert stock.curve_resistance.model_source == "PROJECT_DYNAMICS"
    assert stock.service_braking.model.value == "CONSTANT_EQUIVALENT_BRAKE_FORCE"
    assert stock.etcs_supervision.model_role == "MOVEMENT_AUTHORITY_LOOKAHEAD"
    assert stock.service_braking.reference_deceleration_mps2 >= (
        stock.etcs_supervision.reference_deceleration_mps2
    )


def test_p6_005_regional_stock_carries_its_own_frozen_reference_values():
    """TEST P6-005 - the typed RS-REG200 instance carries its own frozen values."""
    stock = _assert_stock_matches_the_file("RS-REG200")
    assert stock.category.value == "REGIONAL_PASSENGER"
    assert stock.data_status == "SYNTHETIC_REFERENCE"
    assert stock.running_resistance.coefficient_speed_unit == "km/h"
    assert stock.running_resistance.output_force_unit == "kN"
    assert stock.traction.traction_curve is None
    assert stock.service_braking.reference_deceleration_mps2 >= (
        stock.etcs_supervision.reference_deceleration_mps2
    )
    # the two reference stock types are different objects with different values
    hsr = _typed_stock("RS-HSR320")
    assert stock.id != hsr.id
    assert stock.length_m != hsr.length_m
    assert stock.mass.static_mass_t != hsr.mass.static_mass_t
    assert stock.max_speed_kmh < hsr.max_speed_kmh
    assert stock.traction.rated_power_kw < hsr.traction.rated_power_kw


# ---------------------------------------------------------------------------
# TEST P6-006
# ---------------------------------------------------------------------------
def test_p6_006_derived_si_properties_are_recomputed_from_the_stored_fields():
    """TEST P6-006 - the SI properties equal the stored fields, recomputed here."""
    catalogue = _catalogue()
    assert len(catalogue.rolling_stock) == 2
    for stock in catalogue.rolling_stock:
        stored_mass_t = float(stock.mass.static_mass_t)
        factor = float(stock.mass.rotating_mass_factor)
        assert stock.mass_kg == stored_mass_t * 1000.0
        assert stock.length_m == float(stock.geometry.length_m)
        assert stock.effective_mass_kg == stored_mass_t * 1000.0 * factor
        assert stock.effective_mass_kg >= stock.mass_kg, "the allowance cannot reduce the mass"
        assert stock.max_speed_kmh == float(stock.performance_limits.max_speed_kmh)
        assert isinstance(stock.mass_kg, float)
        assert isinstance(stock.effective_mass_kg, float)
        assert isinstance(stock.length_m, float)
    # the properties are read-only: writing one must fail
    stock = _typed_stock("RS-HSR320")
    with pytest.raises(AttributeError):
        stock.mass_kg = 1.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TEST P6-007 ... TEST P6-016 - one rule per test
# ---------------------------------------------------------------------------
def _rejects(allowed_codes: tuple[str, ...], mutate, *, field: str) -> list[Any]:
    """Mutate a copy of the HSR stock, validate it, and return the diagnostics."""
    stock = _copy(_typed_stock("RS-HSR320"))
    mutate(stock)
    diagnostics = _validation_module().validate_rolling_stock(stock)
    assert diagnostics, f"mutating {field} must be reported"
    codes = _codes_of(diagnostics)
    assert any(code in allowed_codes for code in codes), (codes, field)
    fields = _fields_of(diagnostics)
    assert any(field == named or named.endswith(field) for named in fields), (fields, field)
    assert all(diagnostic.severity.value == "ERROR" for diagnostic in diagnostics)
    assert all(diagnostic.object_id == "RS-HSR320" for diagnostic in diagnostics)
    return diagnostics


def test_p6_007_rejects_non_positive_static_mass():
    """TEST P6-007 - static_mass_t = 0.0 and a negative value are both rejected."""
    codes = _codes()
    for value in (0.0, -1.0, -485.0):
        diagnostics = _rejects(
            (codes.VAL_RS_002,),
            lambda stock, value=value: setattr(stock.mass, "static_mass_t", value),
            field="mass.static_mass_t",
        )
        assert codes.VAL_RS_002 in _codes_of(diagnostics)
    # the catalogue form reports the object and the indexed field path
    stock = _copy(_typed_stock("RS-HSR320"))
    stock.mass.static_mass_t = 0.0
    catalogue = _catalogue().model_copy(deep=True)
    catalogue.rolling_stock[0] = stock
    result = _validation_module().validate_rolling_stock_catalogue(catalogue)
    assert result.status.value == "INVALID"
    assert "rolling_stock[0].mass.static_mass_t" in _fields_of(result.diagnostics)
    assert all(code.startswith("VAL-RS-") for code in result.codes())


def test_p6_008_rejects_non_positive_length():
    """TEST P6-008 - length_m = 0.0 and a negative value are both rejected."""
    codes = _codes()
    for value in (0.0, -202.0):
        assert codes.VAL_RS_002 in _codes_of(
            _rejects(
                (codes.VAL_RS_002,),
                lambda stock, value=value: setattr(stock.geometry, "length_m", value),
                field="geometry.length_m",
            )
        )


def test_p6_009_rejects_rotating_mass_factor_below_one():
    """TEST P6-009 - a rotating-mass allowance below 1.0 is rejected."""
    codes = _codes()
    for value in (0.99, 0.0, -1.04):
        diagnostics = _rejects(
            (codes.VAL_RS_003,),
            lambda stock, value=value: setattr(stock.mass, "rotating_mass_factor", value),
            field="mass.rotating_mass_factor",
        )
        assert codes.VAL_RS_003 in _codes_of(diagnostics)
    # exactly 1.0 is accepted (the documented inclusive floor)
    stock = _copy(_typed_stock("RS-HSR320"))
    stock.mass.rotating_mass_factor = 1.0
    assert _validation_module().validate_rolling_stock(stock) == []


def test_p6_010_rejects_non_positive_max_speed():
    """TEST P6-010 - max_speed_kmh <= 0.0 is rejected."""
    codes = _codes()
    for value in (0.0, -320.0):
        assert codes.VAL_RS_002 in _codes_of(
            _rejects(
                (codes.VAL_RS_002,),
                lambda stock, value=value: setattr(stock.performance_limits, "max_speed_kmh", value),
                field="performance_limits.max_speed_kmh",
            )
        )


def test_p6_011_rejects_non_positive_rated_power():
    """TEST P6-011 - rated_power_kw <= 0.0 is rejected."""
    codes = _codes()
    for value in (0.0, -9800.0):
        assert codes.VAL_RS_002 in _codes_of(
            _rejects(
                (codes.VAL_RS_002,),
                lambda stock, value=value: setattr(stock.traction, "rated_power_kw", value),
                field="traction.rated_power_kw",
            )
        )


def test_p6_012_rejects_non_positive_max_tractive_effort():
    """TEST P6-012 - max_tractive_effort_kn <= 0.0 is rejected."""
    codes = _codes()
    for value in (0.0, -300.0):
        assert codes.VAL_RS_002 in _codes_of(
            _rejects(
                (codes.VAL_RS_002,),
                lambda stock, value=value: setattr(stock.traction, "max_tractive_effort_kn", value),
                field="traction.max_tractive_effort_kn",
            )
        )


def test_p6_013_rejects_non_positive_max_operational_acceleration():
    """TEST P6-013 - max_operational_acceleration_mps2 <= 0.0 is rejected."""
    codes = _codes()
    for value in (0.0, -0.65):
        assert codes.VAL_RS_002 in _codes_of(
            _rejects(
                (codes.VAL_RS_002,),
                lambda stock, value=value: setattr(
                    stock.performance_limits, "max_operational_acceleration_mps2", value
                ),
                field="performance_limits.max_operational_acceleration_mps2",
            )
        )


def test_p6_014_rejects_negative_resistance_coefficients():
    """TEST P6-014 - a negative running-resistance coefficient is rejected."""
    codes = _codes()
    for name in ("A", "B", "C"):
        diagnostics = _rejects(
            (codes.VAL_RS_004,),
            lambda stock, name=name: setattr(
                stock.running_resistance.coefficients, name, -0.001
            ),
            field=f"running_resistance.coefficients.{name}",
        )
        assert codes.VAL_RS_004 in _codes_of(diagnostics)
    # zero coefficients are accepted (non-negative, as documented)
    stock = _copy(_typed_stock("RS-HSR320"))
    stock.running_resistance.coefficients.C = 0.0
    assert _validation_module().validate_rolling_stock(stock) == []


def test_p6_015_rejects_non_positive_service_braking_reference():
    """TEST P6-015 - a service-braking reference deceleration <= 0.0 is rejected."""
    codes = _codes()
    for value in (0.0, -0.63):
        assert codes.VAL_RS_002 in _codes_of(
            _rejects(
                (codes.VAL_RS_002,),
                lambda stock, value=value: setattr(
                    stock.service_braking, "reference_deceleration_mps2", value
                ),
                field="service_braking.reference_deceleration_mps2",
            )
        )


def test_p6_016_rejects_non_positive_etcs_reference():
    """TEST P6-016 - an ETCS reference deceleration <= 0.0 is rejected."""
    codes = _codes()
    for value in (0.0, -0.50):
        assert codes.VAL_RS_002 in _codes_of(
            _rejects(
                (codes.VAL_RS_002,),
                lambda stock, value=value: setattr(
                    stock.etcs_supervision, "reference_deceleration_mps2", value
                ),
                field="etcs_supervision.reference_deceleration_mps2",
            )
        )


# ---------------------------------------------------------------------------
# TEST P6-017
# ---------------------------------------------------------------------------
def test_p6_017_rejects_unrecognised_unit_and_model_values():
    """TEST P6-017 - an unrecognised unit or model value is rejected, naming the field."""
    codes = _codes()
    validator = _validation_module()
    model = _model_module()

    # the two unit fields are stored strings: the validator reports them
    for field, value in (("coefficient_speed_unit", "mph"), ("output_force_unit", "lbf")):
        diagnostics = _rejects(
            (codes.VAL_RS_005,),
            lambda stock, field=field, value=value: setattr(
                stock.running_resistance, field, value
            ),
            field=f"running_resistance.{field}",
        )
        assert codes.VAL_RS_005 in _codes_of(diagnostics)

    # the two model fields are typed enumerations: the reader refuses a document that
    # carries an unrecognised value, naming the field
    for block in ("traction", "running_resistance"):
        document = json.loads(json.dumps(_raw_document()))
        document["rolling_stock"][0][block]["model"] = "NOT_A_MODEL"
        with pytest.raises(model.RollingStockError) as excinfo:
            model.load_rolling_stock_catalogue(document)
        assert block in str(excinfo.value) and "model" in str(excinfo.value)

    # an object that bypassed the parser is still reported by the validator
    stock = _copy(_typed_stock("RS-HSR320"))
    unvalidated = model.RollingStockTractiveEffort.model_construct(
        model="NOT_A_MODEL",
        rated_power_kw=stock.traction.rated_power_kw,
        max_tractive_effort_kn=stock.traction.max_tractive_effort_kn,
        traction_curve=None,
    )
    object.__setattr__(stock, "traction", unvalidated)
    diagnostics = validator.validate_rolling_stock(stock)
    assert codes.VAL_RS_005 in _codes_of(diagnostics)
    assert any("traction.model" in field for field in _fields_of(diagnostics))

    # a string is never coerced into a numeric field (strict numbers, no repair)
    document = json.loads(json.dumps(_raw_document()))
    document["rolling_stock"][0]["mass"]["static_mass_t"] = "485.0"
    with pytest.raises(model.RollingStockError) as excinfo:
        model.load_rolling_stock_catalogue(document)
    assert "static_mass_t" in str(excinfo.value)


# ---------------------------------------------------------------------------
# TEST P6-018
# ---------------------------------------------------------------------------
def test_p6_018_rejects_nan_and_infinities_in_numeric_fields():
    """TEST P6-018 - NaN and +inf / -inf are rejected, naming the offending field."""
    codes = _codes()
    infinity = float("inf")
    cases = (
        ("mass", "static_mass_t", float("nan")),
        ("mass", "rotating_mass_factor", infinity),
        ("geometry", "length_m", -infinity),
        ("performance_limits", "max_speed_kmh", float("nan")),
        ("performance_limits", "max_operational_acceleration_mps2", infinity),
        ("traction", "rated_power_kw", -infinity),
        ("traction", "max_tractive_effort_kn", float("nan")),
        ("service_braking", "reference_deceleration_mps2", infinity),
        ("etcs_supervision", "reference_deceleration_mps2", -infinity),
    )
    for block, field, value in cases:
        stock = _copy(_typed_stock("RS-HSR320"))
        setattr(getattr(stock, block), field, value)
        diagnostics = _validation_module().validate_rolling_stock(stock)
        assert codes.VAL_RS_001 in _codes_of(diagnostics), (block, field, _codes_of(diagnostics))
        named = _fields_of(diagnostics)
        assert any(named_field.endswith(f"{block}.{field}") for named_field in named), (
            block, field, named
        )
    for coefficient in ("A", "B", "C"):
        stock = _copy(_typed_stock("RS-HSR320"))
        setattr(stock.running_resistance.coefficients, coefficient, float("nan"))
        diagnostics = _validation_module().validate_rolling_stock(stock)
        assert codes.VAL_RS_001 in _codes_of(diagnostics)
        assert any(
            field.endswith(f"running_resistance.coefficients.{coefficient}")
            for field in _fields_of(diagnostics)
        )
    # the same rule applies through the catalogue form, and the status is INVALID
    stock = _copy(_typed_stock("RS-REG200"))
    stock.etcs_supervision.reference_deceleration_mps2 = float("nan")
    catalogue = _catalogue().model_copy(deep=True)
    catalogue.rolling_stock[1] = stock
    result = _validation_module().validate_rolling_stock_catalogue(catalogue)
    assert result.status.value == "INVALID"
    assert result.error_count == len(result.diagnostics)


# ---------------------------------------------------------------------------
# TEST P6-019
# ---------------------------------------------------------------------------
def _curve_points(pairs: list[tuple[float, float]]) -> list[Any]:
    """Return typed effort-characteristic points for the given (speed, effort) pairs."""
    model = _model_module()
    return [
        model.RollingStockTractiveEffortPoint(speed_kmh=speed, tractive_effort_kn=effort)
        for speed, effort in pairs
    ]


def test_p6_019_effort_characteristic_rules():
    """TEST P6-019 - the optional effort characteristic is validated point by point."""
    codes = _codes()
    validator = _validation_module()
    model = _model_module()

    # a valid strictly increasing characteristic is accepted, stored and reloadable
    good = _copy(_typed_stock("RS-HSR320"))
    good.traction.traction_curve = _curve_points([(0.0, 300.0), (120.0, 300.0), (320.0, 110.0)])
    assert validator.validate_rolling_stock(good) == []
    assert len(good.traction.traction_curve) == 3
    document = json.loads(json.dumps(_raw_document()))
    document["rolling_stock"][0]["traction"]["traction_curve"] = [
        {"speed_kmh": 0.0, "tractive_effort_kn": 300.0},
        {"speed_kmh": 320.0, "tractive_effort_kn": 110.0},
    ]
    reloaded = model.load_rolling_stock_catalogue(document)
    assert validator.validate_rolling_stock_catalogue(reloaded).diagnostics == []
    assert [point.speed_kmh for point in reloaded.rolling_stock[0].traction.traction_curve] == [
        0.0,
        320.0,
    ]

    # a non-finite point is a non-finite number first (VAL-RS-001) and is reported once:
    # the curve rule does not compare a value that is not a number.
    for pairs, expected_field, expected_code in (
        ([(100.0, 300.0)], "traction.traction_curve", codes.VAL_RS_006),
        ([(100.0, 300.0), (100.0, 280.0)], "traction.traction_curve[1].speed_kmh",
         codes.VAL_RS_006),
        ([(150.0, 300.0), (100.0, 280.0)], "traction.traction_curve[1].speed_kmh",
         codes.VAL_RS_006),
        ([(0.0, 300.0), (120.0, 0.0)], "traction.traction_curve[1].tractive_effort_kn",
         codes.VAL_RS_006),
        ([(0.0, 300.0), (120.0, -10.0)], "traction.traction_curve[1].tractive_effort_kn",
         codes.VAL_RS_006),
        ([(float("nan"), 300.0), (120.0, 280.0)], "traction.traction_curve[0].speed_kmh",
         codes.VAL_RS_001),
    ):
        stock = _copy(_typed_stock("RS-HSR320"))
        stock.traction.traction_curve = _curve_points(pairs)
        diagnostics = validator.validate_rolling_stock(stock)
        assert diagnostics, pairs
        assert expected_code in _codes_of(diagnostics), (pairs, _codes_of(diagnostics))
        assert any(expected_field in field for field in _fields_of(diagnostics)), (
            pairs,
            _fields_of(diagnostics),
        )
        assert all(diagnostic.severity.value == "ERROR" for diagnostic in diagnostics)


# ---------------------------------------------------------------------------
# TEST P6-020
# ---------------------------------------------------------------------------
def test_p6_020_unknown_extension_fields_survive_every_level():
    """TEST P6-020 - extension fields at every level survive load -> dump -> load."""
    document = json.loads(json.dumps(_raw_document()))
    document["future_top_level"] = {"kept": True, "list": [1, 2, 3]}
    document["rolling_stock"][0]["future_stock_level"] = {"kept": "stock"}
    document["rolling_stock"][0]["mass"]["future_block_level"] = 42
    document["rolling_stock"][0]["traction"]["future_curve_note"] = ["a", "b"]

    first = _model_module().load_rolling_stock_catalogue(document)
    assert first.model_extra["future_top_level"] == {"kept": True, "list": [1, 2, 3]}
    stock = first.rolling_stock[0]
    assert stock.model_extra["future_stock_level"] == {"kept": "stock"}
    assert stock.mass.model_extra["future_block_level"] == 42
    assert stock.traction.model_extra["future_curve_note"] == ["a", "b"]

    reloaded = _model_module().load_rolling_stock_catalogue(json.loads(_canonical_json(first)))
    assert reloaded.model_extra == first.model_extra
    assert reloaded.rolling_stock[0].model_extra == stock.model_extra
    assert reloaded.rolling_stock[0].mass.model_extra == stock.mass.model_extra
    assert reloaded.rolling_stock[0].traction.model_extra == stock.traction.model_extra
    assert _canonical_json(reloaded) == _canonical_json(first)
    # the delivered file itself declares no unknown field at the stock level
    assert _typed_stock("RS-HSR320").model_extra == {}


# ---------------------------------------------------------------------------
# TEST P6-021
# ---------------------------------------------------------------------------
def test_p6_021_all_four_reader_forms_are_equal_and_do_not_mutate_the_input():
    """TEST P6-021 - mapping, JSON text, Path and file name yield the same catalogue."""
    model = _model_module()
    document = _raw_document()
    snapshot = json.loads(json.dumps(document))

    from_mapping = model.load_rolling_stock_catalogue(document)
    from_text = model.load_rolling_stock_catalogue(_COMPANION_PATH.read_text(encoding="utf-8"))
    from_path = model.load_rolling_stock_catalogue(_COMPANION_PATH)
    from_name = model.load_rolling_stock_catalogue(str(_COMPANION_PATH))
    from_relative_name = model.load_rolling_stock_catalogue("examples/GRR-01-rolling-stock.json")

    expected = _canonical_json(from_mapping)
    for catalogue in (from_text, from_path, from_name, from_relative_name):
        assert _canonical_json(catalogue) == expected
    assert document == snapshot, "loading must not touch the source mapping"
    assert expected == _canonical_json(_catalogue())
    # reading the delivered file twice is bit-identical (determinism)
    assert _canonical_json(model.load_rolling_stock_catalogue(_COMPANION_PATH)) == expected

    # an unreadable file name and a malformed document are refused, never repaired
    with pytest.raises(model.RollingStockError):
        model.load_rolling_stock_catalogue("examples/no-such-rolling-stock-file.json")
    with pytest.raises(model.RollingStockError):
        model.load_rolling_stock_catalogue("{not json}")
    with pytest.raises(model.RollingStockError):
        model.load_rolling_stock_catalogue([1, 2, 3])
    with pytest.raises(model.RollingStockError):
        model.load_rolling_stock_catalogue(None)


# ---------------------------------------------------------------------------
# TEST P6-022
# ---------------------------------------------------------------------------
def test_p6_022_loading_does_not_change_the_frozen_project_or_companion():
    """TEST P6-022 - the frozen project, its hash and the paths companion are untouched."""
    from railway_headway_sim.io.project_io import (
        document_hash,
        import_project_from_data,
        to_normalized_dict,
    )

    project_before = _GRR01_PATH.read_bytes()
    paths_before = _PATHS_COMPANION_PATH.read_bytes()
    companion_before = _COMPANION_PATH.read_bytes()

    project = import_project_from_data(json.loads(project_before.decode("utf-8"))).project
    hash_before = document_hash(to_normalized_dict(project))
    catalogue = _catalogue()
    _validation_module().validate_rolling_stock_catalogue(catalogue)

    assert hash_before == CANONICAL_GRR01_HASH == document_hash(to_normalized_dict(project))
    assert _sha256(_GRR01_PATH) == GRR01_SHA256 == hashlib.sha256(project_before).hexdigest()
    assert _sha256(_PATHS_COMPANION_PATH) == PATHS_COMPANION_SHA256
    assert _PATHS_COMPANION_PATH.read_bytes() == paths_before
    assert _sha256(_COMPANION_PATH) == COMPANION_SHA256
    assert _COMPANION_PATH.read_bytes() == companion_before
    # the frozen project declares no rolling stock of its own
    assert project.rolling_stock is not None
    assert project.rolling_stock.vehicles == []
    assert "rolling_stock" in json.loads(project_before.decode("utf-8"))


# ---------------------------------------------------------------------------
# TEST P6-023
# ---------------------------------------------------------------------------
def test_p6_023_new_modules_import_no_numeric_library_and_no_forbidden_module():
    """TEST P6-023 - the delivered modules add no numeric or forbidden dependency."""
    for path in (_MODEL_MODULE_PATH, _VALIDATION_MODULE_PATH):
        assert path.is_file(), path
        imported = _import_edges(path)
        assert not set(_NUMERIC_LIBRARIES) & {name.split(".")[0] for name in imported}, (
            path.name,
            sorted(imported),
        )
        for edge in imported:
            target = edge.lstrip(".").split(".")[-1]
            assert target not in _FORBIDDEN_IMPORT_TARGETS, (path.name, edge)

    model_edges = _import_edges(_MODEL_MODULE_PATH)
    assert model_edges == {
        "__future__",
        "enum",
        "json",
        "pathlib",
        "pydantic",
        "typing",
        ".base",
    }, sorted(model_edges)
    validation_edges = _import_edges(_VALIDATION_MODULE_PATH)
    assert validation_edges == {
        "__future__",
        "typing",
        "..models.diagnostics",
        "..models.enums",
        "..models.rolling_stock",
        ".",
        ".infrastructure_support",
    }, sorted(validation_edges)
    for edge in model_edges | validation_edges:
        assert not edge.startswith(("..infrastructure", "..physics", "..io", "..app", "..ui")), edge

    # importing the delivered modules is side-effect free and deterministic
    first = _model_module()
    second = importlib.import_module("railway_headway_sim.models.rolling_stock")
    assert first is second
    assert _canonical_json(_catalogue()) == _canonical_json(_catalogue())


# ---------------------------------------------------------------------------
# TEST P6-024
# ---------------------------------------------------------------------------
def test_p6_024_new_modules_carry_no_forbidden_section_d_token():
    """TEST P6-024 - Section-D scan: the new modules carry no forbidden declared name."""
    s1_tokens = _section_tokens("## 2. S1")
    s3_tokens = _section_tokens("## 4. S3")
    allowed_tokens = _section_tokens("## 2.1")
    assert len(s1_tokens) == 9, s1_tokens
    assert len(s3_tokens) == 7, s3_tokens
    assert allowed_tokens == (
        "Davis",
        "Roeckl",
        "rolling resistance",
        "curve resistance",
        "gradient force",
    ), allowed_tokens

    for path in (_MODEL_MODULE_PATH, _VALIDATION_MODULE_PATH):
        names = _declared_names(path)
        assert names, path.name
        for name in names:
            lowered = name.lower()
            for token in s1_tokens:
                assert token not in lowered, f"{path.name}:{name} carries '{token}'"

    # the five allowed tokens stay confined to the physics package: no declared name
    # outside it carries one, and the two delivered modules are clean
    physics_dir = _PACKAGE_DIR / "physics"
    offenders: list[str] = []
    for path in sorted(_PACKAGE_DIR.rglob("*.py")):
        if "tests" in path.parts or path.name in {"codes.py", "grr_audit.py"}:
            continue
        for name in _declared_names(path):
            lowered = name.lower()
            if any(token.lower() in lowered for token in allowed_tokens):
                if physics_dir not in path.parents:
                    offenders.append(f"{path.name}:{name}")
    assert offenders == [], f"an allowed token appears outside the physics package: {offenders}"

    # the delivered *data* names are unaffected by the scan: the stored field names and
    # the enumeration values are values, not declared names
    module = _model_module()
    assert module.RunningResistanceModel.DAVIS.value == "DAVIS"
    assert "traction" in module.RollingStock.model_fields
    assert "running_resistance" in module.RollingStock.model_fields
    assert "traction_curve" in module.RollingStockTractiveEffort.model_fields
