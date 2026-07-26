from frontend.labels import city_count_label

# Shape returned by GET /cities: list[{"city": ..., "state": ...}]
_FULL_CITIES = [{"city": f"City{i}", "state": "State"} for i in range(53)]
_FALLBACK_CITIES = [{"city": f"City{i}", "state": "State"} for i in range(19)]


def test_city_count_label_full_dataset() -> None:
    assert city_count_label(_FULL_CITIES) == "53 cities"


def test_city_count_label_fallback_dataset() -> None:
    assert city_count_label(_FALLBACK_CITIES) == "19 cities"


def test_city_count_label_empty_falls_back_to_generic_phrase() -> None:
    assert city_count_label([]) == "cities"
