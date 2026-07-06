from maa.custom_action import CustomAction
import json
import time

from utils import logger


class LimingjieActionBase(CustomAction):
    LOG_PREFIX = "???Agent"

    def _click(self, controller, x, y, delay_ms, label):
        logger.debug(f"{self.LOG_PREFIX}??: {label} -> ({x}, {y})")
        job = controller.post_click(int(x), int(y))
        job.wait()
        if not job.succeeded:
            logger.error(f"{self.LOG_PREFIX}??: ???? {label} -> ({x}, {y})")
            return False

        if delay_ms > 0:
            time.sleep(delay_ms / 1000)
        return True

    def _parse_params(self, raw_param):
        if not raw_param:
            return {}
        if isinstance(raw_param, dict):
            return raw_param
        return json.loads(raw_param)

    def _normalize_points(self, raw_points, default_points, field_name):
        if raw_points is None:
            return list(default_points)
        if not isinstance(raw_points, list):
            raise ValueError(f"{field_name} ???????")
        return [
            self._normalize_point(point, f"{field_name}[{index}]")
            for index, point in enumerate(raw_points)
        ]

    def _normalize_point(self, point, field_name):
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError(f"{field_name} ??? [x, y] ??")
        return (int(point[0]), int(point[1]))

    def _recognition_count(self, detail):
        if not detail:
            return 0

        filtered = getattr(detail, "filtered_results", None)
        if filtered is not None:
            try:
                return len(filtered)
            except TypeError:
                pass

        raw_detail = getattr(detail, "raw_detail", None)
        if isinstance(raw_detail, dict):
            filtered = raw_detail.get("filtered")
            if isinstance(filtered, list):
                return len(filtered)
            best = raw_detail.get("best")
            if best:
                return 1

        return 1 if bool(getattr(detail, "hit", False)) else 0

    def _recognition_debug(self, detail):
        if not detail:
            return "detail=None"

        parts = []
        box = getattr(detail, "box", None)
        if box is not None:
            parts.append(f"box={box}")

        best = getattr(detail, "best_result", None)
        score = getattr(best, "score", None) if best is not None else None
        if score is not None:
            parts.append(f"score={score}")

        filtered = getattr(detail, "filtered_results", None)
        if filtered is not None:
            try:
                parts.append(f"filtered={len(filtered)}")
            except TypeError:
                parts.append("filtered=?")

        raw_detail = getattr(detail, "raw_detail", None)
        if isinstance(raw_detail, dict):
            raw_best = raw_detail.get("best")
            if isinstance(raw_best, dict) and "score" in raw_best and score is None:
                parts.append(f"score={raw_best.get('score')}")

        return ", ".join(parts) if parts else "detail=available"

    def _wait_connecting_done(self, context, controller, params):
        timeout_ms = int(params.get("connecting_timeout_ms", 12000))
        interval_ms = int(params.get("connecting_check_interval_ms", 500))
        deadline = time.monotonic() + timeout_ms / 1000
        saw_connecting = False

        while time.monotonic() < deadline:
            try:
                image = controller.post_screencap().wait().get()
                detail = context.run_recognition("???_??Connecting??", image)
                if detail and detail.hit:
                    saw_connecting = True
                    logger.debug(f"{self.LOG_PREFIX}: Connecting??????")
                    time.sleep(interval_ms / 1000)
                    continue
                if saw_connecting:
                    logger.info(f"{self.LOG_PREFIX}: Connecting???")
                return True
            except Exception as e:
                logger.warning(f"{self.LOG_PREFIX}Connecting?????????: {e}")
                return True

        logger.warning(f"{self.LOG_PREFIX}: Connecting???????????")
        return False
