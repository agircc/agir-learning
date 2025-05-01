
class DummyProvider:
    """用于调试的模拟LLM提供者"""
    
    def __init__(self, model_name="dummy", **kwargs):
        self.model_name = model_name
        
    def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=1000):
        """生成文本响应"""
        logger.info(f"[DUMMY] Prompt: {prompt}")
        return "This is a dummy response for debugging purposes."
        
    def generate_json(self, prompt, system_prompt=None, response_model=None, temperature=0.7, max_tokens=1000):
        """生成JSON响应"""
        logger.info(f"[DUMMY] JSON Prompt: {prompt}")
        return {"response": "This is a dummy JSON response", "status": "success"}