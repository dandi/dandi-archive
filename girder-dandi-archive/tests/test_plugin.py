import pytest

from girder_dandi_archive import convert_search_to_mongo_query, dandi_search_handler


@pytest.mark.plugin("dandi_archive")
@pytest.mark.parametrize(
    ["string", "expected"],
    [
        ("more_units_than:3", {"meta.number_of_units": {"$gt": 3}}),
        ("more_units_than:3 fewer_units_than:20", {"meta.number_of_units": {"$gt": 3, "$lt": 20}},),
        ("doi:10.1101/354340", {"meta.related_publications": "10.1101/354340"}),
        ("keyword:mouse", {"meta.keywords": "mouse"}),
        ("keyword:mouse keyword:burgle", {"meta.keywords": {"$all": ["mouse", "burgle"]}},),
    ],
)
def test_valid_search_strings(string, expected):
    assert convert_search_to_mongo_query(string) == expected


@pytest.mark.plugin("dandi_archive")
@pytest.mark.parametrize(
    ["string", "error", "message"],
    [
        (":", SyntaxError, "Malformed key value pair"),
        ("key:", SyntaxError, "Malformed key value pair"),
        ("key:key:value", SyntaxError, "Malformed key value pair"),
        (":value", SyntaxError, "Malformed key value pair"),
        ("number_of_shrews:3", ValueError, "Invalid key number_of_shrews"),
        (
            "doi:doi.org/10.1101/354340",
            ValueError,
            "Invalid value doi.org/10.1101/354340 for key doi",
        ),
    ],
)
def test_invalid_search_strings(string, error, message):
    with pytest.raises(error, match=message):
        convert_search_to_mongo_query(string)


@pytest.mark.plugin("dandi_archive")
@pytest.mark.parametrize(["query_string", "expected"], [("abracadabra", {"item": []})])
def test_dandi_search_handler_with_random_string(query_string, expected):
    assert dandi_search_handler(query_string, ["item"]) == expected
