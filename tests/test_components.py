from loadweave.components import DropEmpty, RenameFields, SelectFields

def test_transforms_are_composable():
    record = {"name": "Ada", "city": "London", "unused": 1}
    selected = SelectFields(["name", "city"]).apply(record)
    assert RenameFields({"city": "location"}).apply(selected) == {"name": "Ada", "location": "London"}

def test_drop_empty_filters_blank_values():
    transform = DropEmpty("name")
    assert transform.apply({"name": ""}) is None
    assert transform.apply({"name": "Ada"}) == {"name": "Ada"}

