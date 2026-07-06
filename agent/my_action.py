from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
import json
import os
import time

from utils import logger


@AgentServer.custom_action("my_action_111")
class MyCustomAction(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:

        print("my_action_111 is running!")

        return True

@AgentServer.custom_action("CountLocks")  
class CountLocksAction(CustomAction):  
    def run(self, context, argv):  
        try:
            # 获取识别详情  
            reco_detail = argv.reco_detail  
            # print(f"action自定义识别详情: {reco_detail}") 

            param_json = json.loads(argv.custom_action_param)
            excepted_count = param_json.get("expected_count", None)

            # 解析识别详情获取匹配数量  
            if reco_detail and hasattr(reco_detail, 'best_result'): 

                # 转换为字典以安全访问属性
                custom_result = vars(reco_detail.best_result)
                custom_detail = custom_result.get("detail", {})

                # 从 detail 中获取 raw_detail  
                raw_detail = custom_detail.get("raw_detail", {})  

                # 从 raw_detail 中获取 filtered 列表  
                filtered_list = raw_detail.get("filtered", [])  
                filtered_count = len(filtered_list)

                # print(f"Filtered 列表: {filtered_list}")  
                # print(f"匹配数量: {filtered_count}")

                # 可以将数量存储到上下文中或执行其他逻辑  
                if filtered_count < excepted_count:
                    context.override_next("识别上锁数量", ["开始炼成"])
                    return CustomAction.RunResult(success=True)  
          
        except Exception as e:  
            print(f"处理识别详情时出错: {e}")  
            return CustomAction.RunResult(success=False) 
         
        context.override_next("识别上锁数量", [])
        return CustomAction.RunResult(success=True)
    
@AgentServer.custom_action("SetTermTemplates")  
class SetTermTemplatesAction(CustomAction):  
    def run(self, context, argv):  
        try:
            params = json.loads(argv.custom_action_param)  

            # 根据类型和数值确定模板 
            if 'type' not in params or 'value' not in params:
                logger.error("设置词条模板时出错: 必须包含词条类型和词条数值两个模板")
                return CustomAction.RunResult(success=False)
            
            type_template = params["type"]  
            value_template = params["value"]  
            
            if not isinstance(type_template, str) or not isinstance(value_template, str):
                logger.error("设置词条模板时出错: 模板必须为文件路径字符串")
                return CustomAction.RunResult(success=False)
            
            type_path = f"resource/image/{type_template}"  
            value_path = f"resource/image/{value_template}" 

            if not os.path.isfile(type_path):
                logger.error(f"设置词条模板时出错: 模板文件不存在: {type_path} {os.getcwd()}")
                return CustomAction.RunResult(success=False)
            
            if not os.path.isfile(value_path):
                logger.error(f"设置词条模板时出错: 模板文件不存在: {value_path} {os.getcwd()}")
                return CustomAction.RunResult(success=False)

            # 动态设置所有相关节点的模板  
            override = {  
                "判断词条a类型": {"template": [type_template]},  
                "判断词条b类型": {"template": [type_template]},  
                "判断词条c类型": {"template": [type_template]},  
                "判断词条d类型": {"template": [type_template]},  
                "判断词条a数值": {"template": [value_template]},  
                "判断词条b数值": {"template": [value_template]},  
                "判断词条c数值": {"template": [value_template]},  
                "判断词条d数值": {"template": [value_template]}  
            }  
            context.override_pipeline(override) 

        except Exception as e:  
            logger.error(f"处理识别详情时出错: {e}")  
            return CustomAction.RunResult(success=False) 
        
        return CustomAction.RunResult(success=True)


@AgentServer.custom_action("LimingjieBossFormation")
class LimingjieBossFormationAction(CustomAction):
    LOG_PREFIX = "黎明界BOSS编队"
    SELECTED_CHECK_NODE = "LimingjieFormationSelectedCheck"
    SELECTED_CHECK_TEMPLATES = [
        "jp/limingjie/party_selected_check_1.png",
        "jp/limingjie/party_selected_check_2.png",
        "jp/limingjie/party_selected_check_3.png",
    ]
    DEFAULT_TEAM_TABS = {
        1: (130, 120),
        2: (285, 120),
        3: (445, 120),
    }
    DEFAULT_CARD_CENTERS = [
        (145, 315),
        (285, 315),
        (425, 315),
        (565, 315),
        (705, 315),
        (845, 315),
        (985, 315),
        (1125, 315),
        (145, 455),
        (285, 455),
        (425, 455),
        (565, 455),
        (705, 455),
        (845, 455),
        (985, 455),
    ]

    def run(self, context: Context, argv: CustomAction.RunArg):
        try:
            params = self._parse_params(argv.custom_action_param)
            strategy = params.get("strategy", "top_power_15")
            if strategy != "top_power_15":
                logger.error(f"{self.LOG_PREFIX}失败: 不支持的策略 {strategy}")
                return CustomAction.RunResult(success=False)

            teams = int(params.get("teams", 3))
            members_per_team = int(params.get("members_per_team", 5))
            click_delay_ms = int(params.get("click_delay_ms", 250))
            switch_delay_ms = int(params.get("switch_delay_ms", 800))
            settle_delay_ms = int(params.get("settle_delay_ms", 300))
            setup_ex_equipment = bool(params.get("setup_ex_equipment", False))
            team_tabs = self._normalize_team_tabs(params.get("team_tabs"))
            card_centers = self._normalize_points(
                params.get("card_centers"),
                self.DEFAULT_CARD_CENTERS,
                "card_centers",
            )

            required_cards = teams * members_per_team
            if teams < 1 or members_per_team < 1:
                logger.error(
                    f"{self.LOG_PREFIX}失败: 非法队伍参数 teams={teams}, members_per_team={members_per_team}"
                )
                return CustomAction.RunResult(success=False)
            if len(card_centers) < required_cards:
                logger.error(
                    f"{self.LOG_PREFIX}失败: 候补坐标不足，需要 {required_cards} 个，实际 {len(card_centers)} 个"
                )
                return CustomAction.RunResult(success=False)

            logger.info(
                f"{self.LOG_PREFIX}开始: strategy={strategy}, teams={teams}, members_per_team={members_per_team}, setup_ex_equipment={setup_ex_equipment}"
            )
            logger.debug(f"{self.LOG_PREFIX}节点: {argv.node_name}")
            logger.debug(f"{self.LOG_PREFIX}参数: {params}")

            try:
                context.wait_freezes(time=settle_delay_ms)
            except Exception as e:
                logger.warning(f"{self.LOG_PREFIX}等待画面静止失败，继续执行: {e}")

            controller = context.tasker.controller
            for team in range(1, teams + 1):
                if not self._switch_team(controller, team_tabs, team, switch_delay_ms):
                    return CustomAction.RunResult(success=False)

                begin = (team - 1) * members_per_team
                end = begin + members_per_team
                logger.info(f"{self.LOG_PREFIX}: 开始选择第 {team} 队，候补序号 {begin + 1}-{end}")
                for card_index in range(begin, end):
                    x, y = card_centers[card_index]
                    if not self._select_candidate_if_needed(
                        context,
                        controller,
                        x,
                        y,
                        click_delay_ms,
                        f"第{team}队候补{card_index + 1}",
                        params,
                    ):
                        return CustomAction.RunResult(success=False)

                if setup_ex_equipment and not self._setup_ex_equipment(
                    context,
                    controller,
                    params,
                    f"第{team}队",
                ):
                    return CustomAction.RunResult(success=False)

            if setup_ex_equipment:
                self._wait_connecting_done(context, controller, params)

            logger.info(f"{self.LOG_PREFIX}完成: 已选择前{required_cards}名候补并停留在第{teams}队")
            return CustomAction.RunResult(success=True)
        except Exception:
            logger.exception(f"{self.LOG_PREFIX}执行异常")
            return CustomAction.RunResult(success=False)

    def _switch_team(self, controller, team_tabs, team, delay_ms):
        point = team_tabs.get(team)
        if point is None:
            logger.error(f"{self.LOG_PREFIX}失败: 未配置第 {team} 队切换坐标")
            return False

        x, y = point
        return self._click(controller, x, y, delay_ms, f"切换第{team}队")

    def _click(self, controller, x, y, delay_ms, label):
        logger.debug(f"{self.LOG_PREFIX}点击: {label} -> ({x}, {y})")
        job = controller.post_click(int(x), int(y))
        job.wait()
        if not job.succeeded:
            logger.error(f"{self.LOG_PREFIX}失败: 点击失败 {label} -> ({x}, {y})")
            return False

        if delay_ms > 0:
            time.sleep(delay_ms / 1000)
        return True

    def _select_candidate_if_needed(self, context, controller, x, y, delay_ms, label, params):
        selected = self._is_candidate_selected(context, controller, x, y, params, label)
        if selected is None:
            return False
        if selected:
            logger.info(f"{self.LOG_PREFIX}: {label} 已选中，跳过点击")
            return True

        if not self._click(controller, x, y, delay_ms, label):
            return False

        if not bool(params.get("verify_candidate_selected", True)):
            return True

        selected = self._is_candidate_selected(context, controller, x, y, params, f"{label}点击后")
        if selected is None:
            return False
        if selected:
            logger.debug(f"{self.LOG_PREFIX}: {label} 点击后已确认选中")
            return True

        logger.error(f"{self.LOG_PREFIX}失败: {label} 点击后未识别到已选中标记")
        return False

    def _is_candidate_selected(self, context, controller, x, y, params, label):
        roi = self._candidate_selected_roi(x, y, params)
        threshold = float(params.get("selected_check_threshold", 0.6))
        templates = params.get("selected_check_templates", self.SELECTED_CHECK_TEMPLATES)
        if isinstance(templates, str):
            templates = [templates]

        try:
            image = controller.post_screencap().wait().get()
            detail = context.run_recognition(
                self.SELECTED_CHECK_NODE,
                image,
                pipeline_override={
                    self.SELECTED_CHECK_NODE: {
                        "recognition": "TemplateMatch",
                        "template": templates,
                        "roi": roi,
                        "threshold": threshold,
                        "action": "DoNothing",
                    }
                },
            )
            hit = bool(detail and detail.hit)
            logger.debug(
                f"{self.LOG_PREFIX}已选检查: {label}, hit={hit}, roi={roi}, threshold={threshold}, {self._recognition_debug(detail)}"
            )
            return hit
        except Exception as e:
            if bool(params.get("allow_click_on_selected_check_error", False)):
                logger.warning(f"{self.LOG_PREFIX}已选检查失败: {label}, roi={roi}, 按未选中处理: {e}")
                return False

            logger.error(f"{self.LOG_PREFIX}失败: {label} 已选检查异常，停止以避免反选: roi={roi}, {e}")
            return None

    def _candidate_selected_roi(self, x, y, params):
        offset = params.get("selected_check_roi_offset", [-55, -85])
        size = params.get("selected_check_roi_size", [140, 120])
        if not isinstance(offset, list) or len(offset) != 2:
            raise ValueError("selected_check_roi_offset 必须是 [x, y]")
        if not isinstance(size, list) or len(size) != 2:
            raise ValueError("selected_check_roi_size 必须是 [w, h]")

        roi_x = max(0, int(x) + int(offset[0]))
        roi_y = max(0, int(y) + int(offset[1]))
        return [roi_x, roi_y, int(size[0]), int(size[1])]

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

    def _setup_ex_equipment(self, context, controller, params, team_label):
        ex_button = self._normalize_point(
            params.get("ex_equipment_button", [820, 610]),
            "ex_equipment_button",
        )
        recommend_button = self._normalize_point(
            params.get("ex_recommend_button", [790, 640]),
            "ex_recommend_button",
        )
        recommend_ok_button = self._normalize_point(
            params.get("ex_recommend_ok_button", [790, 640]),
            "ex_recommend_ok_button",
        )
        confirm_button = self._normalize_point(
            params.get("ex_confirm_button", [1085, 640]),
            "ex_confirm_button",
        )
        cancel_button = self._normalize_point(
            params.get("ex_cancel_button", [195, 640]),
            "ex_cancel_button",
        )
        click_delay_ms = int(params.get("ex_click_delay_ms", 700))
        page_delay_ms = int(params.get("ex_page_delay_ms", 1200))

        logger.info(f"{self.LOG_PREFIX}: {team_label} 开始自动EX装备")
        if not self._click(controller, *ex_button, page_delay_ms, "EX装備"):
            return False
        if not self._click(controller, *recommend_button, click_delay_ms, "おまかせ装備"):
            return False
        if not self._click(controller, *recommend_ok_button, page_delay_ms, "おまかせEX装備設定 OK"):
            return False
        if not self._click(controller, *confirm_button, page_delay_ms, "装備確定"):
            return False

        self._wait_connecting_done(context, controller, params)
        if self._is_party_page(context, controller):
            logger.info(f"{self.LOG_PREFIX}: {team_label} EX装备已确定并返回编队页")
            return True

        logger.info(f"{self.LOG_PREFIX}: {team_label} EX装备无变化或仍在设置页，点击取消返回")
        if not self._click(controller, *cancel_button, page_delay_ms, "EX装備設定 キャンセル"):
            return False
        self._wait_connecting_done(context, controller, params)

        if not self._is_party_page(context, controller):
            logger.error(f"{self.LOG_PREFIX}失败: {team_label} EX装备设置后未返回编队页")
            return False

        return True

    def _is_party_page(self, context, controller):
        try:
            image = controller.post_screencap().wait().get()
            detail = context.run_recognition("黎明界_通用编队开始", image)
            return bool(detail and detail.hit)
        except Exception as e:
            logger.warning(f"{self.LOG_PREFIX}编队页确认失败: {e}")
            return False

    def _wait_connecting_done(self, context, controller, params):
        timeout_ms = int(params.get("connecting_timeout_ms", 12000))
        interval_ms = int(params.get("connecting_check_interval_ms", 500))
        deadline = time.monotonic() + timeout_ms / 1000
        saw_connecting = False

        while time.monotonic() < deadline:
            try:
                image = controller.post_screencap().wait().get()
                detail = context.run_recognition("黎明界_通用Connecting等待", image)
                if detail and detail.hit:
                    saw_connecting = True
                    logger.debug(f"{self.LOG_PREFIX}: Connecting中，继续等待")
                    time.sleep(interval_ms / 1000)
                    continue
                if saw_connecting:
                    logger.info(f"{self.LOG_PREFIX}: Connecting已结束")
                return True
            except Exception as e:
                logger.warning(f"{self.LOG_PREFIX}Connecting检测失败，继续执行: {e}")
                return True

        logger.warning(f"{self.LOG_PREFIX}: Connecting等待超时，继续后续流程")
        return False

    def _parse_params(self, raw_param):
        if not raw_param:
            return {}
        if isinstance(raw_param, dict):
            return raw_param
        return json.loads(raw_param)

    def _normalize_team_tabs(self, raw_tabs):
        if raw_tabs is None:
            return dict(self.DEFAULT_TEAM_TABS)

        if isinstance(raw_tabs, dict):
            result = {}
            for key, value in raw_tabs.items():
                result[int(key)] = self._normalize_point(value, f"team_tabs[{key}]")
            return result

        points = self._normalize_points(raw_tabs, [], "team_tabs")
        return {index + 1: point for index, point in enumerate(points)}

    def _normalize_points(self, raw_points, default_points, field_name):
        if raw_points is None:
            return list(default_points)
        if not isinstance(raw_points, list):
            raise ValueError(f"{field_name} 必须是坐标数组")
        return [
            self._normalize_point(point, f"{field_name}[{index}]")
            for index, point in enumerate(raw_points)
        ]

    def _normalize_point(self, point, field_name):
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError(f"{field_name} 必须是 [x, y] 坐标")
        return (int(point[0]), int(point[1]))


@AgentServer.custom_action("LimingjieBattleFormation")
class LimingjieBattleFormationAction(LimingjieBossFormationAction):
    LOG_PREFIX = "黎明界核心战斗编队"
    DEFAULT_CARD_CENTERS = [
        (145, 225),
        (285, 225),
        (425, 225),
        (565, 225),
        (705, 225),
    ]

    def run(self, context: Context, argv: CustomAction.RunArg):
        try:
            params = self._parse_params(argv.custom_action_param)
            strategy = params.get("strategy", "top_power_5")
            if strategy != "top_power_5":
                logger.error(f"{self.LOG_PREFIX}失败: 不支持的策略 {strategy}")
                return CustomAction.RunResult(success=False)

            members_per_team = int(params.get("members_per_team", 5))
            click_delay_ms = int(params.get("click_delay_ms", 250))
            settle_delay_ms = int(params.get("settle_delay_ms", 300))
            setup_ex_equipment = bool(params.get("setup_ex_equipment", True))
            card_centers = self._normalize_points(
                params.get("card_centers"),
                self.DEFAULT_CARD_CENTERS,
                "card_centers",
            )

            if members_per_team < 1:
                logger.error(f"{self.LOG_PREFIX}失败: 非法编队人数 {members_per_team}")
                return CustomAction.RunResult(success=False)
            if len(card_centers) < members_per_team:
                logger.error(
                    f"{self.LOG_PREFIX}失败: 候补坐标不足，需要 {members_per_team} 个，实际 {len(card_centers)} 个"
                )
                return CustomAction.RunResult(success=False)

            logger.info(
                f"{self.LOG_PREFIX}开始: strategy={strategy}, members_per_team={members_per_team}, setup_ex_equipment={setup_ex_equipment}"
            )
            logger.debug(f"{self.LOG_PREFIX}节点: {argv.node_name}")
            logger.debug(f"{self.LOG_PREFIX}参数: {params}")

            try:
                context.wait_freezes(time=settle_delay_ms)
            except Exception as e:
                logger.warning(f"{self.LOG_PREFIX}等待画面静止失败，继续执行: {e}")

            controller = context.tasker.controller
            for card_index in range(members_per_team):
                x, y = card_centers[card_index]
                if not self._select_candidate_if_needed(
                    context,
                    controller,
                    x,
                    y,
                    click_delay_ms,
                    f"候补{card_index + 1}",
                    params,
                ):
                    return CustomAction.RunResult(success=False)

            if setup_ex_equipment and not self._setup_ex_equipment(
                context,
                controller,
                params,
                "核心队伍",
            ):
                return CustomAction.RunResult(success=False)

            self._wait_connecting_done(context, controller, params)
            logger.info(f"{self.LOG_PREFIX}完成: 已选择前{members_per_team}名候补")
            return CustomAction.RunResult(success=True)
        except Exception:
            logger.exception(f"{self.LOG_PREFIX}执行异常")
            return CustomAction.RunResult(success=False)
