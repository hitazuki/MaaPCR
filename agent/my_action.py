from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
import json
import os


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
                print("设置词条模板时出错: 必须包含词条类型和词条数值两个模板")
                return CustomAction.RunResult(success=False)
            
            type_template = params["type"]  
            value_template = params["value"]  
            
            if not isinstance(type_template, str) or not isinstance(value_template, str):
                print("设置词条模板时出错: 模板必须为文件路径字符串")
                return CustomAction.RunResult(success=False)
            
            type_path = f"resource/image/{type_template}"  
            value_path = f"resource/image/{value_template}" 

            if not os.path.isfile(type_path):
                print(f"设置词条模板时出错: 模板文件不存在: {type_path} {os.getcwd()}")
                return CustomAction.RunResult(success=False)
            
            if not os.path.isfile(value_path):
                print(f"设置词条模板时出错: 模板文件不存在: {value_path} {os.getcwd()}")
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
            print(f"处理识别详情时出错: {e}")  
            return CustomAction.RunResult(success=False) 
        
        return CustomAction.RunResult(success=True)