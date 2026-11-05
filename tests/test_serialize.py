import json

import numpy as np
import pandas as pd

from bessy.serialize import to_jsonable


def test_nan_and_inf_become_none():
    out = to_jsonable({"a": float("nan"), "b": np.float64("inf"), "c": 1.5, "d": np.nan})
    assert out == {"a": None, "b": None, "c": 1.5, "d": None}


def test_timestamp_becomes_iso_date():
    assert to_jsonable(pd.Timestamp("2026-10-26 00:00")) == "2026-10-26"
    assert to_jsonable(pd.NaT) is None


def test_dataframe_becomes_records():
    df = pd.DataFrame({"x": np.array([1, 2], dtype="int64"), "y": [0.5, np.nan], "d": pd.to_datetime(["2020-01-01", None])})
    out = to_jsonable(df)
    assert out == [{"x": 1, "y": 0.5, "d": "2020-01-01"}, {"x": 2, "y": None, "d": None}]
    assert type(out[0]["x"]) is int


def test_nested_dict_list_tuple_and_numpy_bool():
    out = to_jsonable({"k": [(1, np.int64(2)), {"z": np.bool_(True)}]})
    assert out == {"k": [[1, 2], {"z": True}]}


def test_output_is_valid_strict_json():
    obj = {"df": pd.DataFrame({"a": [np.nan, 1.0]}), "t": pd.Timestamp("2020-02-02"), "s": pd.Series([1, np.nan])}
    json.dumps(to_jsonable(obj), allow_nan=False)
