from maa.agent.agent_server import AgentServer
from maa.custom_recognition import TemplateMatchResult, CustomRecognition
from maa.context import Context
import json

@AgentServer.custom_recognition("my_reco_222")
class MyRecongition(CustomRecognition):

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:

        reco_detail = context.run_recognition(
            "MyCustomOCR",
            argv.image,
            pipeline_override={"MyCustomOCR": {"roi": [100, 100, 200, 300]}},
        )

        # context is a reference, will override the pipeline for whole task
        context.override_pipeline({"MyCustomOCR": {"roi": [1, 1, 114, 514]}})
        # context.run_recognition ...

        # make a new context to override the pipeline, only for itself
        new_context = context.clone()
        new_context.override_pipeline({"MyCustomOCR": {"roi": [100, 200, 300, 400]}})
        reco_detail = new_context.run_recognition("MyCustomOCR", argv.image)

        click_job = context.tasker.controller.post_click(10, 20)
        click_job.wait()

        context.override_next(argv.node_name, ["TaskA", "TaskB"])

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 100, 100), detail={"detail": "Hello World!"}
        )

def serialize_recognition_result(result):  
    """将 RecognitionResult 对象或列表转换为可序列化的字典"""  
    if result is None:  
        return None  
      
    # 如果是列表，递归处理每个元素  
    if isinstance(result, list):  
        return [serialize_recognition_result(item) for item in result]  
      
    # 检查是否为 TemplateMatchResult (BoxAndScoreResult)  
    if not isinstance(result, TemplateMatchResult):  
        return None  
      
    # 处理 box 的多种格式  
    box = result.box  
    if hasattr(box, 'x'):  
        # Rect 对象  
        box_coords = [box.x, box.y, box.w, box.h]  
    elif isinstance(box, (list, tuple)) and len(box) == 4:  
        # 列表或元组格式  
        box_coords = list(box)  
    else:  
        # 其他格式，返回 None 或默认值  
        return None  
      
    return {  
        "box": box_coords,  
        "score": result.score  
    } 

@AgentServer.custom_recognition("AlwaysTrueTemplateMatch")  
class AlwaysTrueTemplateMatchRecognition(CustomRecognition):  
    def analyze(self, context, argv):  
          
        # 解析参数  
        params = json.loads(argv.custom_recognition_param) if argv.custom_recognition_param else {}  
        template_path = params.get("template", ["default.png"]) 
        threshold = params.get("threshold", 0.7)  
          
        # 调用内置的 TemplateMatch 进行实际匹配  
        try:  
            reco_detail = context.run_recognition(  
                "InternalTemplateMatch",  
                argv.image,  
                pipeline_override={  
                    "InternalTemplateMatch": {  
                        "recognition": "TemplateMatch",  
                        "template": [template_path],  
                        "threshold": threshold,  
                        "roi": [argv.roi.x, argv.roi.y, argv.roi.w, argv.roi.h]  
                    }  
                }  
            )  

            if reco_detail and reco_detail.hit and reco_detail.filtered_results:  
                # 匹配成功，返回实际匹配结果 
                return CustomRecognition.AnalyzeResult(  
                    box=reco_detail.box,  
                    detail={  
                        "raw_detail": reco_detail.raw_detail,  
                        "template": template_path,  
                        "matched": True  
                    }  
                )  
        except Exception as e:  
            print(f"自定义识别 AlwaysTrueTemplateMatch 失败: {e}")  
          
        # 匹配失败，返回默认位置但仍然成功  
        # 使用 ROI 的中心作为默认位置  
        default_x = argv.roi.x + argv.roi.w // 2  
        default_y = argv.roi.y + argv.roi.h // 2  
          
        return CustomRecognition.AnalyzeResult(  
            box=(default_x, default_y, 10, 10),  # 小矩形表示点位置  
            detail={  
                "matched": False,  
                "template": template_path,  
                "default_position": [default_x, default_y]  
            }  
        )