# agents/product_agent/generator.py
import json
from pydantic import BaseModel, Field, ValidationError
from agents.shared.llm import chat_json


# 定义输出格式
class ProductContent(BaseModel):
    title: str = Field(description="商品标题，20字以内")
    description: str = Field(description="商品描述，80-150字")


def generate_product_content(
    category: str,
    spec: str,
    price: float,
    extra_info: str = ""
) -> ProductContent | None:
    """
    输入商品信息，返回 Claude 生成的标题和描述
    失败时返回 None，不抛出异常
    """
    prompt = f"""请根据以下商品信息生成电商平台的商品标题和描述：

品类：{category}
规格/型号：{spec}
售价：¥{price}
补充信息：{extra_info or '无'}

要求：
- 标题：20字以内，包含核心卖点，吸引点击
- 描述：80-150字，突出适用场景和产品优势，语气自然

返回格式（只返回 JSON，不要其他文字）：
{{"title": "...", "description": "..."}}"""

    try:
        raw = chat_json(prompt)
        # 清理可能多余的 markdown 格式
        raw = raw.strip().strip('`')
        if raw.startswith('json'):
            raw = raw[4:].strip()
        data = json.loads(raw)
        return ProductContent(**data)
    except (ValidationError, json.JSONDecodeError, KeyError) as e:
        print(f"  ⚠ 生成失败：{e}")
        return None


def generate_batch(products: list[dict]) -> list[dict]:
    """批量生成，返回原始数据 + 生成内容"""
    results = []
    for i, product in enumerate(products):
        print(f"  处理 {i+1}/{len(products)}: {product.get('name', product.get('sku'))}")
        content = generate_product_content(
            category=product.get("category", ""),
            spec=product.get("spec", ""),
            price=product.get("price", 0),
            extra_info=product.get("extra_info", ""),
        )
        results.append({
            **product,
            "generated_title": content.title if content else "",
            "generated_description": content.description if content else "",
            "status": "generated" if content else "failed",
        })
    return results


if __name__ == "__main__":
    test_products = [
        {"sku": "SKU001", "name": "连帽卫衣", "category": "男装", "spec": "纯棉 M/L/XL", "price": 199},
        {"sku": "SKU002", "name": "运动水杯", "category": "运动配件", "spec": "500ml 不锈钢", "price": 89},
    ]

    print("🤖 开始生成...\n")
    results = generate_batch(test_products)

    for r in results:
        print(f"\n【{r['sku']}】{r['name']}")
        print(f"标题：{r['generated_title']}")
        print(f"描述：{r['generated_description']}")
        print(f"状态：{r['status']}")