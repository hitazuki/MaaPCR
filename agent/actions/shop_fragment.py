"""Bounded, bidirectional searches for selected shop fragments."""

import json
import struct
import time
import zlib
from pathlib import Path

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction

from utils import logger


@AgentServer.custom_action("PrepareShopFragmentSearch")
class PrepareShopFragmentSearch(CustomAction):
    def run(self, context, argv):
        try:
            params = json.loads(argv.custom_action_param)
            overrides = {}
            for name in params["nodes"]:
                node = context.get_node_data(name)
                if node is None:
                    raise ValueError(f"Missing fragment node: {name}")
                recognition = node.get("recognition", "DirectHit")
                kind = recognition.get("type") if isinstance(recognition, dict) else recognition
                # Unselected characters remain DirectHit placeholders.
                if kind != "TemplateMatch":
                    continue
                overrides[name] = {
                    "recognition": "DirectHit",
                    "action": "Custom",
                    "custom_action": "SearchShopFragment",
                    "custom_action_param": {
                        "original_node": node,
                        "max_swipes": params.get("max_swipes", 12),
                    },
                }
            return context.override_pipeline(overrides) if overrides else True
        except Exception:
            logger.exception("碎片搜索初始化失败")
            return False


@AgentServer.custom_action("SearchShopFragment")
class SearchShopFragment(CustomAction):
    def run(self, context, argv):
        try:
            params = json.loads(argv.custom_action_param)
            limit = int(params.get("max_swipes", 12))
            if not 1 <= limit <= 12:
                raise ValueError("max_swipes must be between 1 and 12")
            # Keep the selected template, threshold, ROI and click offset intact.
            # The original Click action must only run in this cloned context.
            probe = context.clone()
            if not probe.override_pipeline({argv.node_name: params["original_node"]}):
                return False
            controller = context.tasker.controller
            image = None
            # Recognize the initial viewport, then after EACH of 24 swipes.
            for attempt in range(2 * limit + 1):
                if context.tasker.stopping:
                    return False
                image = controller.post_screencap().wait().get()
                if image is None:
                    return False
                result = probe.run_recognition(argv.node_name, image)
                if result is None:
                    logger.error(f"碎片识别无法执行: {argv.node_name}")
                    return False
                if result.hit:
                    if context.tasker.stopping:
                        return False
                    action = probe.run_action(argv.node_name, result.box)
                    logger.info(f"碎片搜索命中: {argv.node_name}, 已滑动 {attempt} 次")
                    return bool(action and action.success)
                if attempt == 2 * limit:
                    break
                forward = attempt < limit
                begin_y, end_y = (500, 400) if forward else (400, 500)
                logger.debug(
                    f"碎片搜索: {argv.node_name}, "
                    f"{'正向' if forward else '反向'} {attempt % limit + 1}/{limit}"
                )
                if not controller.post_swipe(550, begin_y, 550, end_y, 200).wait().succeeded:
                    return False
                # Wait for inertia/animation before taking the next screenshot.
                deadline = time.monotonic() + 0.8
                while time.monotonic() < deadline:
                    if context.tasker.stopping:
                        return False
                    time.sleep(0.05)
            self._save_miss(image, argv.node_name)
            logger.warning(
                f"碎片搜索跳过: {argv.node_name}, 正向 {limit} 次、反向 {limit} 次均未找到"
            )
            # Continue to the next character without clicking an unmatched box.
            return True
        except Exception:
            logger.exception(f"碎片搜索执行失败: {argv.node_name}")
            return False

    @staticmethod
    def _save_miss(image, node_name):
        try:
            folder = Path("debug/custom/shop_fragment")
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"miss_{time.time_ns()}.png"
            path.write_bytes(encode_screenshot_png(image))
            logger.warning(f"碎片未找到截图: {node_name}, {path}")
        except Exception:
            logger.exception(f"保存碎片未找到截图失败: {node_name}")


def encode_screenshot_png(image):
    """Encode Maa's BGR screenshot without adding Pillow/OpenCV dependencies."""
    height, width = image.shape[:2]
    rgb = image[:, :, :3][:, :, ::-1]
    pixels = b"".join(b"\0" + row.tobytes() for row in rgb)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")
