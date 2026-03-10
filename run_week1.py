# run_week1.py
from agents.product_agent.validator import load_and_validate
from agents.product_agent.generator import generate_batch

if __name__ == "__main__":
    # 1. 读取并校验
    ready, pending = load_and_validate("data/sample_products.csv")

    # 2. 只对字段完整的商品生成内容
    print("\n🤖 开始生成商品内容...\n")
    results = generate_batch([r.data for r in ready])

    # 3. 打印结果
    print("\n✅ 生成完成：\n")
    for r in results:
        print(f"【{r['sku']}】{r.get('name', '')}")
        print(f"  标题：{r['generated_title']}")
        print(f"  描述：{r['generated_description'][:60]}...")
        print()