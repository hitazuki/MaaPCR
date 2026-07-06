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
                logger.error(f"黎明界BOSS编队失败: 不支持的策略 {strategy}")
                return CustomAction.RunResult(success=False)

            teams = int(params.get("teams", 3))
            members_per_team = int(params.get("members_per_team", 5))
            click_delay_ms = int(params.get("click_delay_ms", 250))
            switch_delay_ms = int(params.get("switch_delay_ms", 800))
            settle_delay_ms = int(params.get("settle_delay_ms", 300))
            team_tabs = self._normalize_team_tabs(params.get("team_tabs"))
            card_centers = self._normalize_points(
                params.get("card_centers"),
                self.DEFAULT_CARD_CENTERS,
                "card_centers",
            )

            required_cards = teams * members_per_team
            if teams < 1 or members_per_team < 1:
                logger.error(
                    f"黎明界BOSS编队失败: 非法队伍参数 teams={teams}, members_per_team={members_per_team}"
                )
                return CustomAction.RunResult(success=False)
            if len(card_centers) < required_cards:
                logger.error(
                    f"黎明界BOSS编队失败: 候补坐标不足，需要 {required_cards} 个，实际 {len(card_centers)} 个"
                )
                return CustomAction.RunResult(success=False)

            logger.info(
                f"黎明界BOSS编队开始: strategy={strategy}, teams={teams}, members_per_team={members_per_team}"
            )
            logger.debug(f"黎明界BOSS编队节点: {argv.node_name}")
            logger.debug(f"黎明界BOSS编队参数: {params}")

            try:
                context.wait_freezes(time=settle_delay_ms)
            except Exception as e:
                logger.warning(f"黎明界BOSS编队等待画面静止失败，继续执行: {e}")

            controller = context.tasker.controller
            for team in range(1, teams + 1):
                if not self._switch_team(controller, team_tabs, team, switch_delay_ms):
                    return CustomAction.RunResult(success=False)

                begin = (team - 1) * members_per_team
                end = begin + members_per_team
                logger.info(f"黎明界BOSS编队: 开始选择第 {team} 队，候补序号 {begin + 1}-{end}")
                for card_index in range(begin, end):
                    x, y = card_centers[card_index]
                    if not self._click(controller, x, y, click_delay_ms, f"候补{card_index + 1}"):
                        return CustomAction.RunResult(success=False)

            logger.info(f"黎明界BOSS编队完成: 已选择前{required_cards}名候补并停留在第{teams}队")
            return CustomAction.RunResult(success=True)
        except Exception:
            logger.exception("黎明界BOSS编队执行异常")
            return CustomAction.RunResult(success=False)

    def _switch_team(self, controller, team_tabs, team, delay_ms):
        point = team_tabs.get(team)
        if point is None:
            logger.error(f"黎明界BOSS编队失败: 未配置第 {team} 队切换坐标")
            return False

        x, y = point
        return self._click(controller, x, y, delay_ms, f"切换第{team}队")

    def _click(self, controller, x, y, delay_ms, label):
        logger.debug(f"黎明界BOSS编队点击: {label} -> ({x}, {y})")
        job = controller.post_click(int(x), int(y))
        job.wait()
        if not job.succeeded:
            logger.error(f"黎明界BOSS编队失败: 点击失败 {label} -> ({x}, {y})")
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
