import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app import database, main
from app.schemas import BlockUpdate, BlockWhatIf, JointBlockRequest, TaskUpdate


class DashboardApiWorkflowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_path = database.DATABASE_PATH
        database.DATABASE_PATH = str(Path(self.temp_dir.name) / "test-api-railplan.db")
        database.initialize()
        self.previous_simulation = main.simulator
        main.simulator = type(main.simulator)(seed=51)

    def tearDown(self):
        main.simulator = self.previous_simulation
        database.DATABASE_PATH = self.previous_path
        self.temp_dir.cleanup()

    async def test_command_dashboard_aggregates_workload_clusters_and_simulated_integrations(self):
        response = main.command_dashboard()
        self.assertTrue(response["simulated"])
        self.assertEqual(set(response["workload"]), {"Engineering", "S&T", "Traction"})
        self.assertTrue(response["clusters"])
        self.assertEqual({source["system"] for source in response["simulation"]["integrations"]}, {"TMS", "SMMS", "TDMS", "COA", "BDMS"})
        self.assertTrue(all(source["external_status"] == "Not connected" for source in response["simulation"]["integrations"]))
        self.assertTrue(all(1 <= task["criticality"] <= 100 for task in response["tasks"]))
        self.assertTrue(all(task["zone"] and task["asset_type"] for task in response["tasks"]))

    async def test_drag_what_if_can_move_block_between_days_and_flags_overlapping_possession(self):
        blocks = database.get_blocks()
        block = blocks[0]
        moved_date = (date.today() + timedelta(days=2)).isoformat()
        result = await main.block_what_if(block["id"], BlockWhatIf(start_time="02:00", date_iso=moved_date))
        self.assertEqual(result["block"]["date_iso"], moved_date)
        self.assertEqual(result["block"]["window"], "02:00 – 05:00")
        self.assertIn(blocks[2]["id"], result["impact"]["conflicting_blocks"])
        self.assertGreater(result["impact"]["estimated_delay_minutes"], 0)
        self.assertTrue(result["approval_required"])

    async def test_controller_edits_persist_and_refresh_dashboard_workload(self):
        task = database.get_tasks()[0]
        block = database.get_blocks()[0]
        updated_task = TaskUpdate(
            asset="Controller-reviewed rail inspection",
            location=task["location"],
            department="S&T",
            source="Manual",
            priority="High",
            due="Due tomorrow",
            duration=2,
            corridor=task["corridor"],
            status="Completed",
            criticality=72,
        )
        with patch.object(main.hub, "publish", new_callable=AsyncMock) as publish:
            result = await main.edit_task(task["id"], updated_task)
        self.assertEqual(result["asset"], "Controller-reviewed rail inspection")
        publish.assert_awaited_once_with({"type": "refresh", "resource": "tasks", "id": task["id"]})
        command = main.command_dashboard()
        self.assertEqual(command["workload"]["Engineering"]["tasks"], 1)
        self.assertEqual(command["workload"]["Engineering"]["overdue"], 0)
        self.assertEqual(next(item for item in command["tasks"] if item["id"] == task["id"])["department"], "S&T")

        block_update = BlockUpdate(
            corridor=block["corridor"],
            section="Controller-updated section",
            date_iso=date.fromisoformat(database.get_blocks()[2]["date_iso"]),
            start_time="02:00",
            duration=3,
            departments=["Engineering", "S&T"],
            tasks=4,
            status="Under review",
            trains=6,
            availability=89.5,
            resources={"manpower": "Confirmed", "machines": "Pending", "materials": "Unavailable"},
            confidence=81,
            reasoning="Controller adjusted this sample block for review.",
        )
        with patch.object(main.hub, "publish", new_callable=AsyncMock) as publish:
            block_result = await main.edit_block(block["id"], block_update)
        self.assertEqual(block_result["block"]["section"], "Controller-updated section")
        self.assertEqual(block_result["block"]["window"], "02:00 – 05:00")
        self.assertEqual(block_result["block"]["resources"]["materials"], "Unavailable")
        self.assertIn(database.get_blocks()[2]["id"], block_result["conflicting_blocks"])
        self.assertTrue(block_result["approval_required"])
        publish.assert_awaited_once_with({"type": "refresh", "resource": "blocks", "id": block["id"]})
        self.assertEqual(main.command_dashboard()["blocks"][0]["status"], "Under review")

    async def test_alert_can_create_an_emergency_proposal_without_granting_a_block(self):
        result = await main.propose_emergency_block("ALT-001")
        self.assertEqual(result["block"]["status"], "Emergency proposal")
        self.assertEqual(result["block"]["resources"]["manpower"], "Pending")
        self.assertTrue(result["simulated"])
        self.assertTrue(result["approval_required"])

    async def test_joint_requisition_records_department_and_readiness_state(self):
        block = database.get_blocks()[0]
        result = await main.joint_block_request(block["id"], JointBlockRequest(
            departments=["Engineering", "S&T"],
            task_ids=["TMS-2841", "SMMS-1092"],
            resources_confirmed=False,
        ))
        self.assertEqual(result["status"], "Resources pending")
        self.assertEqual(database.get_joint_requests()[0]["block_id"], block["id"])
        with self.assertRaises(HTTPException):
            await main.joint_block_request(block["id"], JointBlockRequest(
                departments=["Engineering"], task_ids=["UNKNOWN-TASK"],
            ))


if __name__ == "__main__":
    unittest.main()
