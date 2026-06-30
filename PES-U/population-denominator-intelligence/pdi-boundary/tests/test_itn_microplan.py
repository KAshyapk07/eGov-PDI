import numpy as np
import pandas as pd

from sources import itn_microplan


def _raw(rows):
    """A raw frame in the workbook's column order: path names, then code and label."""
    return pd.DataFrame(rows, columns=itn_microplan._RAW_COLUMNS)


def test_normalize_resolves_levels_and_parents():
    raw = _raw([
        ["Tchad", None, None, None, None, None, "ADMIN_TC", "Tchad"],
        ["Tchad", "OUADDAI", None, None, None, None, "ADMIN_TC_16_OUADDAI", "OUADDAI"],
        ["Tchad", "OUADDAI", "MARFA", None, None, None, "ADMIN_TC_16_11_MARFA", "MARFA"],
        ["Tchad", "OUADDAI", "MARFA", "RIMELE", None, None, "ADMIN_TC_16_11_07_RIMELE", "RIMELE"],
        ["Tchad", "OUADDAI", "MARFA", "RIMELE", "TARA", None, "ADMIN_TC_16_11_07_05_TARA", "TARA"],
    ])

    out = itn_microplan.normalize(raw).set_index("boundary_code")

    assert pd.isna(out.loc["ADMIN_TC", "parent_code"])
    assert out.loc["ADMIN_TC", "level"] == "country"
    assert out.loc["ADMIN_TC_16_OUADDAI", "parent_code"] == "ADMIN_TC"
    # Parent is the enclosing unit, not a code prefix (province code is not a prefix of the district).
    assert out.loc["ADMIN_TC_16_11_MARFA", "parent_code"] == "ADMIN_TC_16_OUADDAI"
    assert out.loc["ADMIN_TC_16_11_07_05_TARA", "level"] == "spp_sfd"
    assert out.loc["ADMIN_TC_16_11_07_05_TARA", "parent_code"] == "ADMIN_TC_16_11_07_RIMELE"


def test_normalize_skips_missing_intermediate_level():
    raw = _raw([
        ["Tchad", "P", None, None, None, None, "ADMIN_TC_P", "P"],
        ["Tchad", "P", "D", None, None, None, "ADMIN_TC_P_D", "D"],
        ["Tchad", "P", "D", "HC", None, None, "ADMIN_TC_P_D_HC", "HC"],
        ["Tchad", "P", "D", "HC", None, "VLG", "ADMIN_TC_P_D_HC_VLG", "VLG"],
    ])

    out = itn_microplan.normalize(raw).set_index("boundary_code")

    assert out.loc["ADMIN_TC_P_D_HC_VLG", "level"] == "village"
    assert out.loc["ADMIN_TC_P_D_HC_VLG", "parent_code"] == "ADMIN_TC_P_D_HC"


def test_normalize_drops_rows_without_a_code_and_fills_blank_label():
    raw = _raw([
        ["Tchad", "P", None, None, None, None, "ADMIN_TC_P", np.nan],
        ["Tchad", "P", "D", None, None, None, None, "D"],
    ])

    out = itn_microplan.normalize(raw)

    assert list(out["boundary_code"]) == ["ADMIN_TC_P"]
    assert out.loc[0, "name"] == "P"
