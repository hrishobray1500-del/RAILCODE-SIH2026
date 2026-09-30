import tempfile
import unittest
from pathlib import Path

from app import database
from app.planner import generate_plan


class CoordinationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_path = database.DATABASE_PATH
        database.DATABASE_PATH = str(Path(self.temp_dir.name) / "test-railplan.db")
        database.initialize()

    def tearDown(self):
        database.DATABASE_PATH = self.previous_path
        self.temp_dir.cleanup()

    def test_seeded_command_data_contains_explanations_resources_and_real_dates(self):
        blocks = database.get_blocks()
        self.assertEqual(len(blocks), 3)
        self.assertTrue(all(block["date_iso"] for block in blocks))
        self.assertTrue(all(block["resources"]["machines"] for block in blocks))
        self.assertTrue(all(block["reasoning"] for block in blocks))
        self.assertTrue(all(1 <= block["confidence"] <= 100 for block in blocks))

    def test_what_if_override_changes_block_time_and_leaves_it_proposed(self):
        before = database.get_blocks()[0]
        moved = database.move_block(before["id"], "02:15", before["date_iso"])
        self.assertIsNotNone(moved)
        self.assertEqual(moved["window"], "02:15 – 05:15")
        self.assertEqual(moved["status"], "Proposed")
        self.assertEqual(moved["date_iso"], before["date_iso"])
        self.assertEqual(database.get_blocks()[0]["id"], before["id"])

    def test_joint_request_records_all_departments_and_resource_readiness(self):
        block = database.get_blocks()[0]
        request = database.create_joint_request(block["id"], {
            "departments": ["Engineering", "S&T"],
            "task_ids": ["TMS-2841", "SMMS-1092"],
            "resources_confirmed": True,
        })
        self.assertEqual(request["status"], "Ready for review")
        stored = database.get_joint_requests()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["departments"], ["Engineering", "S&T"])
        self.assertTrue(stored[0]["resources_confirmed"])

    def test_generated_plan_contains_confidence_reasoning_and_resource_status(self):
        blocks, _ = generate_plan(database.get_tasks(), "This week")
        self.assertTrue(blocks)
        for block in blocks:
            self.assertGreaterEqual(block["confidence"], 78)
            self.assertIn("verify", block["reasoning"].lower())
            self.assertIn("manpower", block["resources"])
            self.assertTrue(block["date_iso"])


if __name__ == "__main__":
    unittest.main()
