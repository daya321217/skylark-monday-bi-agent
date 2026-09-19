import pandas as pd
from data_model import parse_money, normalize_board

def test_parse_money():
    assert parse_money("₹1,234,567.00") == 1234567.0
    assert pd.isna(parse_money(None))
    assert pd.isna(parse_money("not a number"))

def test_normalize_board():
    raw = {
        "meta": {"columns": [
            {"id":"sector","title":"Sector","type":"dropdown"},
            {"id":"value","title":"Masked Deal value","type":"numbers"},
            {"id":"date","title":"Created Date","type":"date"},
        ]},
        "items": [{
            "id":"1","name":"A","created_at":None,"updated_at":None,
            "column_values":[
                {"id":"sector","text":"Mining","value":"{}","type":"dropdown"},
                {"id":"value","text":"100000","value":"{}","type":"numbers"},
                {"id":"date","text":"2026-01-10","value":"{}","type":"date"},
            ]
        }]
    }
    df = normalize_board(raw, "deals")
    assert df.loc[0,"sector"] == "Mining"
    assert df.loc[0,"deal_value"] == 100000
    assert str(df.loc[0,"created_date"].date()) == "2026-01-10"
