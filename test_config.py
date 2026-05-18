from app.config import Config

cfg = Config()
run_cfg = cfg.get_run_config()

print("=" * 50)
print("✅ 配置加载成功！")
print("=" * 50)
print(f"默认模式: {run_cfg.mode}")
print(f"默认 Ticks: {run_cfg.ticks}")
print(f"默认温度: {run_cfg.temperature}")
print(f"LLM 可用: {cfg.is_llm_available()}")
if cfg.is_llm_available():
    llm_cfg = cfg.get_llm_config()
    print(f"LLM 模型: {llm_cfg.model}")
    print(f"LLM 地址: {llm_cfg.base_url}")
    print(f"API Key: {llm_cfg.api_key[:10]}...")
print("=" * 50)
print("\n提示：如果要使用 LLM 模式，请在 .env 文件中填写 OPENAI_API_KEY")
