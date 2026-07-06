from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
import re
import time

from utils import logger
from actions.limingjie_base import LimingjieActionBase


@AgentServer.custom_action("LimingjieShopPurchase")
class LimingjieShopPurchaseAction(LimingjieActionBase):
    LOG_PREFIX = "黎明界SHOP购买"
    SHOP_TITLE_NODE = "黎明界_SHOP商店标题"
    SHOP_CONFIRM_NODE = "黎明界_SHOP购买确认OK"
    SHOP_COMPLETE_NODE = "黎明界_SHOP购买完成OK"
    SHOP_INSUFFICIENT_NODE = "黎明界_SHOP购买不足停止购买"
    SHOP_SOLD_OUT_NODE = "黎明界_SHOP首个道具位SOLDOUT停止购买"
    CHARACTER_CUTIN_NODE = "黎明界_角色特写跳过点击"
    CHARACTER_JOIN_NODE = "黎明界_通用角色加入关闭"
    SHOP_OCR_BALANCE_NODE = "LimingjieShopBalanceOcr"
    SHOP_OCR_PRICE_NODE = "LimingjieShopFirstPriceOcr"

    def run(self, context: Context, argv: CustomAction.RunArg):
        try:
            params = self._parse_params(argv.custom_action_param)
            controller = context.tasker.controller

            max_purchase_count = int(params.get("max_purchase_count", 20))
            click_delay_ms = int(params.get("shop_click_delay_ms", 500))
            settle_delay_ms = int(params.get("shop_settle_delay_ms", 300))
            buy_button = self._normalize_point(
                params.get("first_buy_button", [330, 350]),
                "first_buy_button",
            )

            logger.info(f"{self.LOG_PREFIX}开始: 固定循环购买第一个商品，max_purchase_count={max_purchase_count}")
            logger.debug(f"{self.LOG_PREFIX}节点: {argv.node_name}")
            logger.debug(f"{self.LOG_PREFIX}参数: {params}")

            try:
                context.wait_freezes(time=settle_delay_ms)
            except Exception as e:
                logger.warning(f"{self.LOG_PREFIX}等待画面静止失败，继续执行: {e}")

            purchased_count = 0
            for attempt in range(1, max_purchase_count + 1):
                if self._is_sold_out(context, controller, params):
                    logger.info(f"{self.LOG_PREFIX}: 首个商品已售罄，停止购买")
                    break

                balance = self._read_shop_number(context, controller, params, "balance")
                price = self._read_shop_number(context, controller, params, "price")
                if balance is None or price is None:
                    logger.error(f"{self.LOG_PREFIX}失败: 无法识别余额或价格，停止购买以避免误点")
                    break

                logger.info(f"{self.LOG_PREFIX}: 第{attempt}次购买前余额={balance}, 首个价格={price}")
                if balance < price:
                    logger.info(f"{self.LOG_PREFIX}: 余额不足 {balance} < {price}，停止购买并关闭商店")
                    break

                buy_x, buy_y = buy_button
                if not self._click(controller, buy_x, buy_y, click_delay_ms, f"购买第一个商品({attempt})"):
                    return CustomAction.RunResult(success=False)

                result = self._wait_purchase_result(context, controller, params)
                if result == "purchased":
                    purchased_count += 1
                    continue
                if result in ("insufficient", "sold_out"):
                    logger.info(f"{self.LOG_PREFIX}: 购买结果={result}，停止购买")
                    break
                if result == "shop":
                    logger.warning(f"{self.LOG_PREFIX}: 点击后仍停留商店页，按未进入购买流程处理并停止")
                    break

                logger.error(f"{self.LOG_PREFIX}失败: 未能确认购买结果，result={result}")
                return CustomAction.RunResult(success=False)

            logger.info(f"{self.LOG_PREFIX}完成: 本次购买成功次数={purchased_count}，准备关闭商店")
            return CustomAction.RunResult(success=True)
        except Exception:
            logger.exception(f"{self.LOG_PREFIX}执行异常")
            return CustomAction.RunResult(success=False)

    def _read_shop_number(self, context, controller, params, kind):
        if kind == "balance":
            node_name = self.SHOP_OCR_BALANCE_NODE
            roi = params.get("balance_roi", [990, 640, 185, 65])
            label = "余额"
        elif kind == "price":
            node_name = self.SHOP_OCR_PRICE_NODE
            roi = params.get("first_price_roi", [120, 320, 240, 80])
            label = "首个价格"
        else:
            raise ValueError(f"未知数字类型: {kind}")

        retry_count = int(params.get("ocr_retry_count", 3))
        retry_delay_ms = int(params.get("ocr_retry_delay_ms", 250))
        for attempt in range(1, retry_count + 1):
            value, text = self._run_shop_ocr(context, controller, node_name, roi)
            logger.debug(f"{self.LOG_PREFIX}OCR: {label} 第{attempt}次 value={value}, text={text!r}, roi={roi}")
            if value is not None:
                return value
            if retry_delay_ms > 0:
                time.sleep(retry_delay_ms / 1000)

        logger.warning(f"{self.LOG_PREFIX}: {label} OCR失败，roi={roi}")
        return None

    def _run_shop_ocr(self, context, controller, node_name, roi):
        image = controller.post_screencap().wait().get()
        detail = context.run_recognition(
            node_name,
            image,
            pipeline_override={
                node_name: {
                    "recognition": "OCR",
                    "roi": roi,
                    "expected": "\\d",
                    "action": "DoNothing",
                }
            },
        )
        texts = self._extract_ocr_texts(detail)
        text = " ".join(texts)
        return self._parse_number(text), text

    def _extract_ocr_texts(self, detail):
        texts = []

        def walk(value):
            if value is None:
                return
            if isinstance(value, str):
                if value.strip():
                    texts.append(value.strip())
                return
            if isinstance(value, dict):
                for key in ("text", "rec_text", "label", "content"):
                    text = value.get(key)
                    if isinstance(text, str) and text.strip():
                        texts.append(text.strip())
                for nested in value.values():
                    walk(nested)
                return
            if isinstance(value, (list, tuple)):
                for item in value:
                    walk(item)
                return
            for attr in ("text", "rec_text", "label", "content"):
                text = getattr(value, attr, None)
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())
            for attr in ("raw_detail", "detail", "best_result", "filtered_results", "all_results"):
                nested = getattr(value, attr, None)
                if nested is not None:
                    walk(nested)

        walk(detail)
        seen = []
        for text in texts:
            if text not in seen:
                seen.append(text)
        return seen

    def _parse_number(self, text):
        if not text:
            return None
        digits = re.findall(r"\d[\d,\.]*", text)
        if not digits:
            return None
        numbers = []
        for item in digits:
            normalized = re.sub(r"[^\d]", "", item)
            if normalized:
                numbers.append(int(normalized))
        if not numbers:
            return None
        return max(numbers)

    def _wait_purchase_result(self, context, controller, params):
        timeout_ms = int(params.get("purchase_result_timeout_ms", 12000))
        interval_ms = int(params.get("purchase_result_check_interval_ms", 250))
        confirm_button = self._normalize_point(
            params.get("purchase_confirm_button", [785, 580]),
            "purchase_confirm_button",
        )
        complete_button = self._normalize_point(
            params.get("purchase_complete_button", [645, 500]),
            "purchase_complete_button",
        )
        click_delay_ms = int(params.get("shop_dialog_click_delay_ms", 700))
        shop_fallback_after_ms = int(params.get("shop_fallback_after_buy_ms", 2500))
        start_time = time.monotonic()
        deadline = time.monotonic() + timeout_ms / 1000

        while time.monotonic() < deadline:
            image = controller.post_screencap().wait().get()
            if self._recognize_node(context, image, "黎明界_通用Connecting等待"):
                time.sleep(interval_ms / 1000)
                continue
            if self._recognize_node(context, image, self.SHOP_CONFIRM_NODE):
                confirm_x, confirm_y = confirm_button
                if not self._click(controller, confirm_x, confirm_y, click_delay_ms, "购买确认OK"):
                    return "click_failed"
                continue
            if self._recognize_node(context, image, self.SHOP_COMPLETE_NODE):
                complete_x, complete_y = complete_button
                if not self._click(controller, complete_x, complete_y, click_delay_ms, "购买完成OK"):
                    return "click_failed"
                if self._wait_shop_page(context, controller, params):
                    return "purchased"
                continue
            if self._recognize_node(context, image, self.SHOP_INSUFFICIENT_NODE):
                return "insufficient"
            if self._recognize_node(context, image, self.SHOP_SOLD_OUT_NODE):
                return "sold_out"
            if self._recognize_node(context, image, self.CHARACTER_CUTIN_NODE):
                if not self._click(controller, 640, 240, click_delay_ms, "商店购买角色特写跳过"):
                    return "click_failed"
                continue
            if self._recognize_node(context, image, self.CHARACTER_JOIN_NODE):
                if not self._click(controller, 640, 580, click_delay_ms, "商店购买角色加入关闭"):
                    return "click_failed"
                continue
            if self._recognize_node(context, image, self.SHOP_TITLE_NODE):
                if time.monotonic() - start_time < shop_fallback_after_ms / 1000:
                    time.sleep(interval_ms / 1000)
                    continue
                stable_ms = int(params.get("shop_stable_after_buy_ms", 1000))
                if stable_ms > 0:
                    time.sleep(stable_ms / 1000)
                image = controller.post_screencap().wait().get()
                if self._recognize_node(context, image, self.SHOP_TITLE_NODE):
                    return "shop"

            time.sleep(interval_ms / 1000)

        return "timeout"

    def _wait_shop_page(self, context, controller, params):
        timeout_ms = int(params.get("shop_page_timeout_ms", 5000))
        interval_ms = int(params.get("shop_page_check_interval_ms", 250))
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            image = controller.post_screencap().wait().get()
            if self._recognize_node(context, image, self.SHOP_TITLE_NODE):
                return True
            time.sleep(interval_ms / 1000)
        return False

    def _is_sold_out(self, context, controller, params):
        image = controller.post_screencap().wait().get()
        return self._recognize_node(context, image, self.SHOP_SOLD_OUT_NODE)

    def _recognize_node(self, context, image, node_name):
        try:
            detail = context.run_recognition(node_name, image)
            hit = bool(detail and detail.hit)
            logger.debug(f"{self.LOG_PREFIX}识别: {node_name}, hit={hit}, {self._recognition_debug(detail)}")
            return hit
        except Exception as e:
            logger.warning(f"{self.LOG_PREFIX}识别失败: {node_name}: {e}")
            return False
