"""Common utilities that are used in all rest tests."""

NAME_1 = "test dandiset 1 name"
DESCRIPTION_1 = "Zzzz! This sorts last."
NAME_2 = "test dandiset 2 name"
DESCRIPTION_2 = "Aaaa! This sorts first."


def assert_dandisets_are_equal(expected, actual):
    assert expected["access"] == actual["access"]
    assert expected["baseParentId"] == actual["baseParentId"]
    assert expected["baseParentType"] == actual["baseParentType"]
    # TODO created datetime
    assert expected["creatorId"] == actual["creatorId"]
    assert expected["description"] == actual["description"]
    assert expected["lowerName"] == actual["lowerName"]
    assert expected["meta"] == actual["meta"]
    assert expected["name"] == actual["name"]
    assert expected["parentCollection"] == actual["parentCollection"]
    assert expected["parentId"] == actual["parentId"]
    assert expected["public"] == actual["public"]
    assert expected["size"] == actual["size"]
    # TODO updated datetime
