"""Scan selected shop fragments once, including disabled purchase-limit cards."""

import copy
import hashlib
import json
import struct
import time
import zlib
from pathlib import Path

import numpy as np
from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction

from utils import logger


LIST_ROI = [330, 200, 900, 350]
LIMIT_NODE = "ShopFragmentPurchaseLimit"


def recognition_params(node):
    recognition = node.get("recognition", "DirectHit")
    if isinstance(recognition, dict):
        return recognition.get("type"), recognition.get("param", {})
    return recognition, node


def gray_template(path):
    digest = hashlib.sha1(path.encode("utf-8")).hexdigest()[:16]
    return f"role/shop_gray/{digest}.png"


def gray_image(image):
    bgr = image[:, :, :3].astype(np.uint32)
    gray = ((bgr[:, :, 2] * 299 + bgr[:, :, 1] * 587 + bgr[:, :, 0] * 114 + 500) // 1000).astype(np.uint8)
    return np.repeat(gray[:, :, None], 3, axis=2)


def same_view(before, after):
    # Ignore the sidebar, balance, selected count and scrollbar animations.
    a = before[200:550:4, 340:1230:4, :3].astype(np.int16)
    b = after[200:550:4, 340:1230:4, :3].astype(np.int16)
    delta = np.abs(a - b)
    return float(delta.mean()) < 1.5 and float((delta > 12).mean()) < 0.01


@AgentServer.custom_action("PrepareShopFragmentSearch")
class PrepareShopFragmentSearch(CustomAction):
    def run(self, context, argv):
        try:
            params = json.loads(argv.custom_action_param)
            selected = {}
            for name in params["nodes"]:
                node = context.get_node_data(name)
                if node is None:
                    raise ValueError(f"Missing fragment node: {name}")
                kind, _ = recognition_params(node)
                if kind == "TemplateMatch":
                    selected[name] = node
            scan = params["scan_node"]
            return context.override_pipeline({scan: {
                "action": "Custom",
                "custom_action": "ScanShopFragments",
                "custom_action_param": {
                    "selected": selected,
                    "purchase_node": params["purchase_node"],
                    "home_node": params["home_node"],
                    "max_pages": params.get("max_pages", 40),
                },
                "next": [params["purchase_node"]],
            }})
        except Exception:
            logger.exception("碎片扫描初始化失败")
            return False


@AgentServer.custom_action("ScanShopFragments")
class ScanShopFragments(CustomAction):
    def run(self, context, argv):
        try:
            params = json.loads(argv.custom_action_param)
            pending = dict(params["selected"])
            if not pending:
                return context.override_next(argv.node_name, [params["home_node"]])
            self.deadline = time.monotonic() + 240
            probe = context.clone()
            originals = copy.deepcopy(pending)
            overrides = {}
            for name, node in originals.items():
                _, recognition = recognition_params(node)
                match = dict(recognition)
                match["roi"] = LIST_ROI
                match["roi_offset"] = [0, 0, 0, 0]
                overrides[name] = {**node, "recognition": {"type": "TemplateMatch", "param": match}}
                templates = match["template"]
                if isinstance(templates, str):
                    templates = [templates]
                overrides[name + "_gray"] = {
                    "recognition": {"type": "TemplateMatch", "param": {
                        **match, "template": [gray_template(t) for t in templates],
                    }},
                    "action": "DoNothing",
                }
            if not probe.override_pipeline(overrides):
                return False
            if not context.override_next(argv.node_name, [params["purchase_node"]]):
                return False
            # The four-category strip is fixed in the three JP fragment shops.
            if self._stopped(context) or not context.tasker.controller.post_click(670, 168).wait().succeeded:
                return False
            if not self._settle(context):
                return False
            image = self._capture(context)
            selected_count = capped_count = unchanged = 0
            max_pages = max(1, min(60, int(params.get("max_pages", 40))))
            for page in range(1, max_pages + 1):
                logger.info(f"碎片逐屏扫描: 第 {page} 屏，待处理 {len(pending)} 个角色")
                # Each click gets a fresh frame before checking other cards.
                while pending:
                    if self._stopped(context):
                        return False
                    limit = self._recognize(probe, LIMIT_NODE, image)
                    gray = gray_image(image) if limit.hit else None
                    clicked = False
                    for name in list(pending):
                        if self._stopped(context):
                            return False
                        result = self._recognize(probe, name, image)
                        if not result.hit and gray is not None:
                            result = self._recognize(probe, name + "_gray", gray)
                            # A gray-only match is ONLY accepted with a limit marker.
                            gray_only = True
                        else:
                            gray_only = False
                        if not result.hit:
                            continue
                        x, y, w, h = result.box
                        # Defer cards whose status text is clipped by either edge.
                        if y < 200 or y + max(h, 170) > 550:
                            continue
                        roi = [max(330, x - 45), y + 70, min(205, 1230 - max(330, x - 45)), 100]
                        capped = self._recognize(probe, LIMIT_NODE, image, {"roi": roi}).hit
                        if capped:
                            pending.pop(name)
                            capped_count += 1
                            logger.info(f"碎片已达购买上限，跳过: {name}")
                            continue
                        if gray_only:
                            continue
                        action = probe.run_action(name, result.box)
                        if not action or not action.success:
                            return False
                        pending.pop(name)
                        selected_count += 1
                        logger.info(f"碎片已勾选: {name}，第 {page} 屏")
                        if not self._settle(context, 0.2):
                            return False
                        image = self._capture(context)
                        clicked = True
                        break
                    if not clicked:
                        break
                if not pending:
                    break
                if page == max_pages:
                    logger.warning("碎片扫描达到页数上限")
                    break
                previous = image
                if not self._swipe(context, 500, 400, 400):
                    return False
                image = self._capture(context)
                unchanged = unchanged + 1 if same_view(previous, image) else 0
                if unchanged >= 2:
                    logger.info("碎片扫描已到列表底部")
                    break
            if pending:
                self._save_miss(image, ", ".join(pending))
                logger.warning(f"碎片扫描未找到: {', '.join(pending)}")
            logger.info(f"碎片扫描完成: 勾选 {selected_count} 个，达到上限 {capped_count} 个，未找到 {len(pending)} 个")
            if not selected_count:
                return context.override_next(argv.node_name, [params["home_node"]])
            return True
        except Exception:
            logger.exception("碎片逐屏扫描执行失败")
            return False

    @staticmethod
    def _capture(context):
        # Agent IPC controller proxies can be invalidated by nested actions.
        # Obtain the current handle immediately before every controller request.
        image = context.tasker.controller.post_screencap().wait().get()
        if image is None:
            raise RuntimeError("Fragment shop screenshot failed")
        return image

    @staticmethod
    def _recognize(probe, name, image, params=None):
        overrides = {name: {"recognition": {"type": "TemplateMatch", "param": params}}} if params else {}
        # Keep one probe alive for the entire scan. Temporary cloned contexts
        # introduce additional Agent IPC proxy lifetimes for every card.
        if params:
            original = probe.get_node_data(name)
            if original is None:
                raise RuntimeError(f"Fragment recognition node missing: {name}")
            try:
                result = probe.run_recognition(name, image, overrides)
            finally:
                if not probe.override_pipeline({name: original}):
                    raise RuntimeError(f"Fragment recognition restore failed: {name}")
        else:
            result = probe.run_recognition(name, image)
        if result is None:
            raise RuntimeError(f"Fragment recognition failed: {name}")
        return result

    def _swipe(self, context, begin_y, end_y, duration):
        if self._stopped(context):
            return False
        job = context.tasker.controller.post_swipe(780, begin_y, 780, end_y, duration).wait()
        return job.succeeded and self._settle(context)

    def _stopped(self, context):
        return context.tasker.stopping or time.monotonic() >= self.deadline

    def _settle(self, context, seconds=0.8):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if self._stopped(context):
                return False
            time.sleep(0.05)
        return not self._stopped(context)

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
    """Encode Maa's BGR screenshot without Pillow/OpenCV dependencies."""
    height, width = image.shape[:2]
    rgb = image[:, :, :3][:, :, ::-1]
    pixels = b"".join(b"\0" + row.tobytes() for row in rgb)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")
