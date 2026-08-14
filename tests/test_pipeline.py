import json
from loadweave.components import JsonlSink, RenameFields, SelectFields
from loadweave.pipeline import Pipeline

class Items:
    def read(self):
        yield {"first": "Ada", "city": "London", "extra": True}
        yield {"first": "Grace", "city": "New York", "extra": True}

def test_pipeline_streams_and_reports_counts(tmp_path):
    output = tmp_path / "result.jsonl"
    pipeline = Pipeline(Items(), [SelectFields(["first", "city"]), RenameFields({"first": "name"})], JsonlSink(str(output)))
    result = pipeline.run()
    assert (result.extracted, result.loaded) == (2, 2)
    assert [json.loads(line) for line in output.read_text().splitlines()] == [{"name": "Ada", "city": "London"}, {"name": "Grace", "city": "New York"}]

