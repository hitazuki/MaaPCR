"""Run with the repository's Maa Python environment; no device required."""

import json
import struct
import sys
import unittest
import zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from actions.shop_fragment import PrepareShopFragmentSearch, SearchShopFragment, encode_screenshot_png


class FragmentSearchTests(unittest.TestCase):
    def search(self, hit_after=None, stopping=False, swipe_success=True):
        job = Mock(succeeded=swipe_success)
        job.wait.return_value = job
        capture = Mock()
        capture.wait.return_value = capture
        capture.get.return_value = object()
        controller = Mock()
        controller.post_screencap.return_value = capture
        controller.post_swipe.return_value = job
        probe = Mock()
        probe.override_pipeline.return_value = True
        count = 0

        def recognize(*args):
            nonlocal count
            hit = count == hit_after
            count += 1
            return SimpleNamespace(hit=hit, box=[100, 200, 89, 76])

        probe.run_recognition.side_effect = recognize
        probe.run_action.return_value = SimpleNamespace(success=True)
        context = Mock(tasker=SimpleNamespace(controller=controller, stopping=stopping))
        context.clone.return_value = probe
        argv = SimpleNamespace(node_name="Fragment", custom_action_param=json.dumps({
            "original_node": {"recognition": "TemplateMatch", "action": "Click"},
            "max_swipes": 12,
        }))
        # Eliminate animation waits without changing recognition or swipe order.
        clock = iter(range(200))
        with patch("actions.shop_fragment.time.monotonic", side_effect=lambda: next(clock)), \
             patch.object(SearchShopFragment, "_save_miss") as save:
            result = SearchShopFragment().run(context, argv)
        return result, controller, probe, save

    def test_initial_hit_does_not_swipe(self):
        result, controller, probe, _ = self.search(hit_after=0)
        self.assertTrue(result)
        controller.post_swipe.assert_not_called()
        probe.run_action.assert_called_once_with("Fragment", [100, 200, 89, 76])

    def test_last_forward_swipe_is_recognized(self):
        result, controller, _, _ = self.search(hit_after=12)
        self.assertTrue(result)
        self.assertEqual(controller.post_swipe.call_count, 12)
        self.assertTrue(all(c.args == (550, 500, 550, 400, 200)
                            for c in controller.post_swipe.call_args_list))

    def test_first_reverse_swipe_is_recognized(self):
        result, controller, _, _ = self.search(hit_after=13)
        self.assertTrue(result)
        self.assertEqual(controller.post_swipe.call_count, 13)
        self.assertEqual(controller.post_swipe.call_args.args, (550, 400, 550, 500, 200))

    def test_last_reverse_swipe_is_recognized(self):
        result, controller, probe, save = self.search(hit_after=24)
        self.assertTrue(result)
        self.assertEqual(controller.post_swipe.call_count, 24)
        probe.run_action.assert_called_once()
        save.assert_not_called()

    def test_missing_fragment_is_skipped_without_click(self):
        result, controller, probe, save = self.search()
        self.assertTrue(result)
        self.assertEqual(controller.post_swipe.call_count, 24)
        self.assertEqual(probe.run_recognition.call_count, 25)
        probe.run_action.assert_not_called()
        save.assert_called_once()

    def test_each_character_has_its_own_budget(self):
        for _ in range(2):
            result, controller, _, _ = self.search()
            self.assertTrue(result)
            self.assertEqual(controller.post_swipe.call_count, 24)

    def test_screenshot_png_preserves_size_and_colors(self):
        image = np.array([[[0, 0, 255], [255, 0, 0]]], dtype=np.uint8)
        png = encode_screenshot_png(image)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", png[16:24]), (2, 1))
        length = struct.unpack(">I", png[33:37])[0]
        self.assertEqual(zlib.decompress(png[41:41 + length]), b"\0\xff\0\0\0\0\xff")

    def test_stop_prevents_actions(self):
        result, controller, probe, _ = self.search(stopping=True)
        self.assertFalse(result)
        controller.post_swipe.assert_not_called()
        probe.run_action.assert_not_called()

    def test_failed_swipe_aborts_search(self):
        result, controller, probe, save = self.search(swipe_success=False)
        self.assertFalse(result)
        self.assertEqual(controller.post_swipe.call_count, 1)
        probe.run_action.assert_not_called()
        save.assert_not_called()

    def test_prepare_preserves_selected_configuration_and_skips_placeholders(self):
        selected = {"recognition": {"type": "TemplateMatch", "param": {
            "template": ["role/example.png"], "threshold": 0.9}},
            "action": {"type": "Click", "param": {"target_offset": [110, 0, -70, -60]}}}
        context = Mock()
        context.get_node_data.side_effect = [selected, {"recognition": {"type": "DirectHit"}}]
        context.override_pipeline.return_value = True
        argv = SimpleNamespace(custom_action_param=json.dumps({"nodes": ["selected", "disabled"]}))
        self.assertTrue(PrepareShopFragmentSearch().run(context, argv))
        overrides = context.override_pipeline.call_args.args[0]
        self.assertEqual(list(overrides), ["selected"])
        self.assertEqual(overrides["selected"]["custom_action_param"]["original_node"], selected)


if __name__ == "__main__":
    unittest.main()
