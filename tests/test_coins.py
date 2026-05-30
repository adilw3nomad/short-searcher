from short_searcher import coins


def test_extracts_ticker_word():
    assert coins.extract_coins("XRP is about to explode", "") == ["XRP"]


def test_extracts_from_name_case_insensitive():
    assert coins.extract_coins("Why bitcoin is surging", "") == ["BTC"]


def test_dedupes_ticker_and_name():
    out = coins.extract_coins("BTC update", "Bitcoin looking strong")
    assert out == ["BTC"]


def test_multiple_coins_sorted():
    assert coins.extract_coins("ETH vs SOL", "") == ["ETH", "SOL"]


def test_no_false_positive_substring():
    # "scam" must not match "ADA" etc.; a bare unrelated word returns nothing
    assert coins.extract_coins("this is a scam warning", "") == []


def test_name_resolves_to_ticker():
    assert coins.COIN_MAP["LUNC"] == "Terra Luna Classic"
