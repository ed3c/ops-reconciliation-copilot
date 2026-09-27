import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
EXP=ROOT/"experiments"

class ExperimentCatalogTests(unittest.TestCase):
    def test_catalog_templates_are_complete_and_unique(self):
        catalog=json.loads((EXP/"catalog.json").read_text())
        self.assertEqual(catalog["schema_version"],"ops-learning-experiment-catalog@1")
        ids=[x["id"] for x in catalog["templates"]]
        self.assertEqual(len(ids),5)
        self.assertEqual(len(ids),len(set(ids)))
        for item in catalog["templates"]:
            path=ROOT/item["path"]
            self.assertTrue(path.is_file())
            data=json.loads(path.read_text())
            self.assertEqual(data["id"],item["id"])
            self.assertIn(data["product_change"],{"EXPERIMENT_FIRST","NO_RUNTIME_CHANGE_REQUIRED","EXPERIMENT_OR_NO_CHANGE"})
            self.assertTrue(data["promotion_gate"])
            self.assertTrue(data["evidence"])
    def test_templates_do_not_turn_curriculum_into_product_authority(self):
        for path in (EXP/"templates").glob("*.json"):
            data=json.loads(path.read_text())
            text=json.dumps(data,ensure_ascii=False)
            self.assertNotIn("AUTO_PROMOTE",text)
            self.assertNotIn("MUST_IMPLEMENT",text)
    def test_example_is_explicitly_historical(self):
        catalog=json.loads((EXP/"catalog.json").read_text())
        example=catalog["examples"][0]
        self.assertEqual(example["status"],"HISTORICAL_EVIDENCE_ONLY")
        for rel in example["evidence"]:
            self.assertTrue((ROOT/rel).is_file(), rel)

if __name__=="__main__":
    unittest.main()
