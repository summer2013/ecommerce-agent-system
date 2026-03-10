# agents/product_agent/validator.py
import pandas as pd
from dataclasses import dataclass, field

# 必填：缺了不能生成
REQUIRED_FIELDS = ["sku", "category", "spec", "price"]
# 选填：缺了可以生成但质量差一点
OPTIONAL_FIELDS = ["name", "extra_info"]


@dataclass
class ValidationResult:
    sku: str
    is_valid: bool
    missing_required: list = field(default_factory=list)
    missing_optional: list = field(default_factory=list)
    data: dict = field(default_factory=dict)


def validate_row(row: pd.Series) -> ValidationResult:
    missing_required = []
    missing_optional = []

    for f in REQUIRED_FIELDS:
        if pd.isna(row.get(f)) or str(row.get(f, "")).strip() == "":
            missing_required.append(f)

    for f in OPTIONAL_FIELDS:
        if pd.isna(row.get(f)) or str(row.get(f, "")).strip() == "":
            missing_optional.append(f)

    return ValidationResult(
        sku=str(row.get("sku", "UNKNOWN")),
        is_valid=len(missing_required) == 0,
        missing_required=missing_required,
        missing_optional=missing_optional,
        data=row.to_dict(),
    )


def load_and_validate(csv_path: str) -> tuple[list, list]:
    """
    读取 CSV，返回 (可生成列表, 待补充列表)
    """
    df = pd.read_csv(csv_path)
    print(f"📂 读取：{csv_path}，共 {len(df)} 条\n")

    ready, pending = [], []

    for _, row in df.iterrows():
        result = validate_row(row)
        if result.is_valid:
            ready.append(result)
            extra = f"缺选填：{result.missing_optional}" if result.missing_optional else "字段完整"
            print(f"  ✅ {result.sku:8}  {extra}")
        else:
            pending.append(result)
            print(f"  ⚠  {result.sku:8}  缺必填：{result.missing_required}")

    print(f"\n📊 可生成 {len(ready)} 条，待补充 {len(pending)} 条")
    return ready, pending


if __name__ == "__main__":
    ready, pending = load_and_validate("data/sample_products.csv")
    if pending:
        print("\n需要补充以下商品的字段：")
        for r in pending:
            print(f"  - {r.sku}：缺 {', '.join(r.missing_required)}")