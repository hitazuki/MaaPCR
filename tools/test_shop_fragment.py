"""Fragment scanning regression tests; no device required."""
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from actions.shop_fragment import LIMIT_NODE, PrepareShopFragmentSearch, ScanShopFragments, gray_image, same_view


def detail(hit=False, box=(395, 245, 90, 77)):
    return SimpleNamespace(hit=hit, box=box)


class FragmentScanTests(unittest.TestCase):
    def scan(self, names, recognize, stopping=False):
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        controller = Mock()
        controller.post_click.return_value.wait.return_value.succeeded = True
        probe = Mock()
        probe.override_pipeline.return_value = True
        probe.run_action.return_value = SimpleNamespace(success=True)
        context = Mock(tasker=SimpleNamespace(controller=controller, stopping=stopping))
        context.clone.return_value = probe
        context.override_next.return_value = True
        params = {
            "selected": {n: {"recognition": "TemplateMatch", "template": "role/a.png", "action": "Click"} for n in names},
            "purchase_node": "Purchase", "home_node": "Home", "max_pages": 4,
        }
        argv = SimpleNamespace(node_name="Scan", custom_action_param=json.dumps(params))
        scanner = ScanShopFragments()
        with patch.object(scanner, "_capture", return_value=image), \
             patch.object(scanner, "_settle", return_value=True), \
             patch.object(scanner, "_swipe", return_value=True) as swipe, \
             patch.object(scanner, "_recognize", side_effect=recognize), \
             patch.object(scanner, "_save_miss") as save:
            result = scanner.run(context, argv)
        return result, context, probe, swipe, save

    def test_all_visible_roles_are_selected_once_and_finish_early(self):
        result, context, probe, swipe, save = self.scan(["a", "b"], lambda p, n, i, params=None: detail(n != LIMIT_NODE))
        self.assertTrue(result)
        self.assertEqual([c.args[0] for c in probe.run_action.call_args_list], ["a", "b"])
        swipe.assert_not_called(); save.assert_not_called()
        context.override_next.assert_called_with("Scan", ["Purchase"])

    def test_capped_gray_role_is_skipped_while_normal_role_is_selected(self):
        def recognize(probe, name, image, params=None):
            if name == LIMIT_NODE:
                return detail(params is None or params["roi"][0] == 350)
            if name == "a":
                return detail(False)
            return detail(True, (395 if name == "a_gray" else 622, 245, 90, 77))
        result, _, probe, _, save = self.scan(["a", "b"], recognize)
        self.assertTrue(result)
        probe.run_action.assert_called_once_with("b", (622, 245, 90, 77))
        save.assert_not_called()

    def test_limit_on_adjacent_card_does_not_mark_normal_role_capped(self):
        result, _, probe, _, _ = self.scan(["a"], lambda p, n, i, params=None: detail(params is None if n == LIMIT_NODE else True))
        self.assertTrue(result); probe.run_action.assert_called_once()

    def test_gray_match_without_limit_on_same_card_is_never_clicked(self):
        def recognize(probe, name, image, params=None):
            return detail(params is None if name == LIMIT_NODE else name.endswith("_gray"))
        result, context, probe, swipe, save = self.scan(["a"], recognize)
        self.assertTrue(result); probe.run_action.assert_not_called()
        self.assertEqual(swipe.call_count, 2)
        save.assert_called_once()
        context.override_next.assert_called_with("Scan", ["Home"])

    def test_all_capped_roles_return_home_without_purchase(self):
        result, context, probe, _, save = self.scan(["a", "b"], lambda *args: detail(True))
        self.assertTrue(result); probe.run_action.assert_not_called(); save.assert_not_called()
        context.override_next.assert_called_with("Scan", ["Home"])

    def test_clipped_card_is_deferred_until_fully_visible(self):
        calls = 0
        def recognize(probe, name, image, params=None):
            nonlocal calls
            if name == LIMIT_NODE:
                return detail(False)
            calls += 1
            return detail(True, (395, 450 if calls == 1 else 290, 90, 77))
        result, _, probe, swipe, _ = self.scan(["a"], recognize)
        self.assertTrue(result); self.assertEqual(swipe.call_count, 1)
        probe.run_action.assert_called_once_with("a", (395, 290, 90, 77))

    def test_no_selection_returns_home_without_device_actions(self):
        result, context, probe, _, _ = self.scan([], lambda *args: detail())
        self.assertTrue(result)
        context.tasker.controller.post_click.assert_not_called(); probe.run_action.assert_not_called()

    def test_stop_prevents_click(self):
        result, context, probe, _, _ = self.scan(["a"], lambda *args: detail(), stopping=True)
        self.assertFalse(result)
        context.tasker.controller.post_click.assert_not_called(); probe.run_action.assert_not_called()

    def test_prepare_uses_only_selected_roles(self):
        selected = {"recognition": {"type": "TemplateMatch", "param": {"template": ["role/a.png"]}}}
        context = Mock()
        context.get_node_data.side_effect = [selected, {"recognition": "DirectHit"}]
        context.override_pipeline.return_value = True
        argv = SimpleNamespace(custom_action_param=json.dumps({
            "nodes": ["a", "b"], "scan_node": "Scan", "purchase_node": "Purchase", "home_node": "Home",
        }))
        self.assertTrue(PrepareShopFragmentSearch().run(context, argv))
        override = context.override_pipeline.call_args.args[0]["Scan"]
        self.assertEqual(override["custom_action_param"]["selected"], {"a": selected})
        self.assertEqual(override["next"], ["Purchase"])

    def test_boundary_comparison_ignores_changing_sidebar(self):
        a = np.zeros((720, 1280, 3), dtype=np.uint8)
        b = a.copy(); b[:, :300] = 255; b[560:] = 255
        self.assertTrue(same_view(a, b))
        b[240:450, 400:600] = 255
        self.assertFalse(same_view(a, b))

    def test_gray_image_preserves_dimmed_avatar_contrast(self):
        image = np.array([[[0, 0, 255], [255, 0, 0]]], dtype=np.uint8)
        np.testing.assert_array_equal(gray_image(image), [[[76, 76, 76], [29, 29, 29]]])

    def test_capture_reacquires_controller_after_nested_action(self):
        controllers = [Mock(), Mock()]
        frames = [object(), object()]
        for controller, frame in zip(controllers, frames):
            controller.post_screencap.return_value.wait.return_value.get.return_value = frame
        class Tasker:
            accesses = 0
            @property
            def controller(self):
                controller = controllers[self.accesses]
                self.accesses += 1
                return controller
        context = SimpleNamespace(tasker=Tasker())
        self.assertIs(ScanShopFragments._capture(context), frames[0])
        self.assertIs(ScanShopFragments._capture(context), frames[1])
        self.assertEqual(context.tasker.accesses, 2)

    def test_card_roi_restored_without_temporary_clone(self):
        probe = Mock()
        original = {"recognition": {"type": "TemplateMatch", "param": {"roi": [330, 200, 900, 350]}}}
        probe.get_node_data.return_value = original
        probe.override_pipeline.return_value = True
        probe.run_recognition.return_value = detail(True)
        result = ScanShopFragments._recognize(probe, LIMIT_NODE, object(), {"roi": [350, 315, 205, 100]})
        self.assertTrue(result.hit)
        probe.clone.assert_not_called()
        probe.override_pipeline.assert_called_once_with({LIMIT_NODE: original})

    def test_card_roi_restored_even_when_recognition_raises(self):
        probe = Mock()
        original = {"recognition": "TemplateMatch"}
        probe.get_node_data.return_value = original
        probe.override_pipeline.return_value = True
        probe.run_recognition.side_effect = RuntimeError("recognition failed")
        with self.assertRaises(RuntimeError):
            ScanShopFragments._recognize(probe, LIMIT_NODE, object(), {"roi": [350, 315, 205, 100]})
        probe.override_pipeline.assert_called_once_with({LIMIT_NODE: original})


if __name__ == "__main__":
    unittest.main()
