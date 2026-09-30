import unittest
from datetime import date

from app.planner import generate_plan
from app.simulation import DemoSimulator


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.tasks = [
            {"id": "TMS-1", "department": "Engineering", "corridor": "BPL–ET", "duration": 3, "criticality": 96, "priority": "Critical", "due": "Overdue 2 days"},
            {"id": "SMMS-1", "department": "S&T", "corridor": "BPL–ET", "duration": 1, "criticality": 84, "priority": "High", "due": "Due today"},
            {"id": "TDMS-1", "department": "Traction", "corridor": "BINA–BPL", "duration": 3, "criticality": 79, "priority": "High", "due": "Due in 1 day"},
        ]

    def test_combines_departments_on_same_corridor(self):
        blocks, scheduled = generate_plan(self.tasks, "This week")
        bpl_blocks = [block for block in blocks if block["corridor"] == "BPL–ET"]
        self.assertEqual(len(bpl_blocks), 1)
        self.assertEqual(bpl_blocks[0]["departments"], ["Engineering", "S&T"])
        self.assertEqual(bpl_blocks[0]["duration"], 4)
        self.assertEqual(scheduled, {"TMS-1", "SMMS-1", "TDMS-1"})

    def test_horizon_limits_windows_and_preserves_task_coverage(self):
        blocks, scheduled = generate_plan(self.tasks, "This week")
        self.assertTrue(all(date.today().strftime("%b") in block["date"] for block in blocks))
        self.assertEqual(len(scheduled), len(self.tasks))
        self.assertTrue(all(block["duration"] <= 4 for block in blocks))

    def test_critical_overdue_work_is_packed_first(self):
        tasks = [
            {"id": "TMS-1", "department": "Engineering", "corridor": "BPL–ET", "duration": 4, "criticality": 96, "priority": "Critical", "due": "Overdue 2 days"},
            {"id": "TMS-2", "department": "Engineering", "corridor": "BPL–ET", "duration": 4, "criticality": 30, "priority": "Low", "due": "Due in 8 days"},
        ]
        blocks, scheduled = generate_plan(tasks, "This week")
        self.assertEqual(blocks[0]["duration"], 4)
        self.assertEqual(len(scheduled), 2)

    def test_respects_monthly_planning_horizon(self):
        tasks = [
            {"id": f"TMS-{index}", "department": "Engineering", "corridor": "BPL–ET", "duration": 4, "criticality": 80, "priority": "High", "due": "Due today"}
            for index in range(10)
        ]
        blocks, scheduled = generate_plan(tasks, "This month")
        self.assertGreaterEqual(len(blocks), 4)
        self.assertEqual(len(scheduled), 10)

    def test_completed_in_progress_and_cancelled_tasks_are_not_scheduled(self):
        tasks = [
            {**self.tasks[0], "status": "Completed"},
            {**self.tasks[1], "status": "In progress"},
            {**self.tasks[2], "status": "Cancelled"},
            {**self.tasks[2], "id": "TDMS-2"},
        ]
        blocks, scheduled = generate_plan(tasks, "This week")
        self.assertEqual(scheduled, {"TDMS-2"})
        self.assertEqual(sum(block["tasks"] for block in blocks), 1)


class DemoSimulatorTests(unittest.TestCase):
    def test_running_simulation_changes_telemetry_within_bounded_ranges(self):
        simulator = DemoSimulator(seed=21)
        before = simulator.snapshot()
        after = simulator.advance()
        self.assertNotEqual(before["network_availability"], after["network_availability"])
        self.assertEqual(len(after["corridors"]), 4)
        self.assertEqual(len(after["history"]), 8)
        self.assertEqual(set(after["workload"]), {"Engineering", "S&T", "Traction"})
        self.assertTrue(all(metrics["tasks"] >= metrics["overdue"] for metrics in after["workload"].values()))
        self.assertTrue(94 <= after["network_availability"] <= 98.3)
        self.assertTrue(96.5 <= after["critical_asset_availability"] <= 99.4)
        self.assertTrue(all(88 <= corridor["availability"] <= 99.7 for corridor in after["corridors"]))
        self.assertTrue(all(21 <= corridor["trains"] <= 48 for corridor in after["corridors"]))

    def test_simulation_can_pause_and_speed_changes_simulated_steps(self):
        simulator = DemoSimulator(seed=8)
        simulator.set_running(False)
        unchanged = simulator.snapshot()
        self.assertFalse(unchanged["running"])
        paused_tick = simulator.tick()
        self.assertEqual(paused_tick["network_availability"], unchanged["network_availability"])
        self.assertEqual(paused_tick["history"], unchanged["history"])
        simulator.set_speed(4)
        self.assertEqual(simulator.snapshot()["speed"], 4)
        advanced = simulator.tick()
        self.assertEqual(advanced["network_availability"], unchanged["network_availability"])
        self.assertEqual(advanced["blocks_scheduled"], unchanged["blocks_scheduled"])
        self.assertEqual(advanced["history"], unchanged["history"])
        simulator.set_running(True)
        advanced = simulator.tick()
        self.assertEqual(len(advanced["history"]), 8)
        self.assertTrue(simulator.snapshot()["running"])

    def test_simulator_rejects_unsupported_speed(self):
        simulator = DemoSimulator(seed=3)
        with self.assertRaises(ValueError):
            simulator.set_speed(3)

    def test_simulator_remains_within_bounds_over_long_run(self):
        simulator = DemoSimulator(seed=19)
        for _ in range(500):
            state = simulator.advance()
        self.assertTrue(94 <= state["network_availability"] <= 98.3)
        self.assertTrue(96.5 <= state["critical_asset_availability"] <= 99.4)
        self.assertTrue(8 <= state["blocks_scheduled"] <= 15)
        self.assertTrue(18 <= state["tasks_coordinated"] <= 30)
        self.assertTrue(all(21 <= corridor["trains"] <= 48 for corridor in state["corridors"]))
        self.assertEqual(len(state["history"]), 12)
        self.assertTrue(all(0 <= metrics["overdue"] <= metrics["tasks"] for metrics in state["workload"].values()))

    def test_reset_restores_default_simulation_controls_and_values(self):
        simulator = DemoSimulator(seed=4)
        simulator.set_running(False)
        simulator.set_speed(4)
        state = simulator.reset()
        self.assertTrue(state["running"])
        self.assertEqual(state["speed"], 1)
        self.assertEqual(state["network_availability"], 96.4)
        self.assertEqual(state["blocks_scheduled"], 11)
        self.assertEqual(len(state["history"]), 7)


if __name__ == "__main__":
    unittest.main()
