# 示例数据集说明

本目录包含用于演示和测试AI财务助手的示例数据集，包括银行流水、信用卡账单、科目表和分类规则。

## 📁 文件列表

### 1. sample_bank_statement.csv
**银行流水示例**
- **用途**: 模拟真实银行账户的交易记录
- **记录数**: 16条交易
- **时间范围**: 2024年1月
- **字段说明**:
  - `Date`: 交易日期 (YYYY-MM-DD)
  - `Description`: 交易描述
  - `Amount`: 交易金额 (正数为收入，负数为支出)
  - `Balance`: 账户余额
  - `Reference`: 交易参考号
  - `Category`: 预分类 (用于验证AI分类效果)

**交易类型覆盖**:
- 💰 收入：工资、客户付款
- 🛒 费用：办公用品、软件订阅、差旅、餐饮
- 💳 其他：ATM取款、银行手续费

### 2. sample_credit_card.csv
**信用卡账单示例**
- **用途**: 企业信用卡的SaaS订阅费用
- **记录数**: 13条交易
- **时间范围**: 2024年1月
- **字段说明**:
  - `Transaction Date`: 交易日期
  - `Posted Date`: 入账日期
  - `Card No.`: 信用卡号码(脱敏)
  - `Description`: 商户名称和服务描述
  - `Category`: 费用类别
  - `Debit`: 支出金额
  - `Credit`: 收入金额(退款等)

**主要商户**:
- 💻 软件服务: Zoom, Dropbox, Adobe, GitHub
- ☁️ 云服务: AWS, Google Workspace
- 📈 营销工具: LinkedIn, HubSpot, Canva

### 3. chart_of_accounts.csv
**会计科目表**
- **用途**: 标准企业会计科目分类
- **记录数**: 25个科目
- **符合标准**: 中小企业会计准则
- **字段说明**:
  - `Account Code`: 科目代码 (4位数字)
  - `Account Name`: 科目名称
  - `Account Type`: 科目类型 (Asset, Liability, Equity, Income, Expense, etc.)
  - `Parent Account`: 父级科目(用于多级科目)
  - `Tax Line`: 税务申报行
  - `Description`: 科目说明

**科目结构**:
```
1000-1999: 资产类
  1000: 现金及现金等价物
  1100: 应收账款
  1400: 设备
2000-2999: 负债类  
  2000: 应付账款
  2100: 信用卡负债
3000-3999: 权益类
  3000: 所有者权益
4000-4999: 收入类
  4100: 服务收入
6000-7999: 费用类
  6100: 办公用品
  6200: 软件
  6300: 营销
```

### 4. classification_rules.csv
**智能分类规则表**
- **用途**: AI分类系统的学习规则
- **记录数**: 25条规则
- **置信度范围**: 0.85-0.98
- **字段说明**:
  - `Keyword`: 关键词/正则表达式
  - `Account Code`: 建议的科目代码
  - `Account Name`: 科目名称
  - `Confidence`: 置信度 (0-1)
  - `Rule Type`: 规则类型 (keyword, regex, pattern)
  - `Created Date`: 规则创建日期

**规则类型**:
- 🔍 **关键词匹配**: amazon → 办公用品
- 🎯 **商户名匹配**: starbucks → 餐饮娱乐
- 💼 **行业标识**: software → 软件费用

### 5. quickbooks_*.csv
**QuickBooks导出模板**

#### quickbooks_journal_template.csv
- **用途**: QuickBooks借贷记账导入
- **格式**: 标准QBO Journal Entry
- **字段**: Date, Account, Debits, Credits, Memo, Entity

#### quickbooks_expense_template.csv
- **用途**: QuickBooks费用记录导入
- **格式**: 标准QBO Expense Entry
- **字段**: Date, Payee, Account, Amount, Memo, Payment method

### 6. xero_bank_transactions.csv
**Xero导出模板**
- **用途**: Xero银行交易导入
- **格式**: 标准Xero Bank Transaction
- **字段**: Date*, Amount*, Payee, Description*, Reference*, AnalysisCode
- **注**: *号字段为必填

## 🔧 使用说明

### 导入测试数据
```bash
# 后端API测试
curl -X POST "http://localhost:8000/api/v1/transactions/upload" \
  -F "file=@sample_bank_statement.csv" \
  -F "source=bank_statement"

curl -X POST "http://localhost:8000/api/v1/transactions/upload" \
  -F "file=@sample_credit_card.csv" \
  -F "source=credit_card"
```

### 分类规则测试
```bash
# 导入分类规则
curl -X POST "http://localhost:8000/api/v1/classification/rules/import" \
  -F "file=@classification_rules.csv"
```

### 科目表导入
```bash
# 导入会计科目
curl -X POST "http://localhost:8000/api/v1/accounts/import" \
  -F "file=@chart_of_accounts.csv"
```

## 📊 数据质量指标

### 银行流水数据
- ✅ 零缺失值
- ✅ 日期格式统一
- ✅ 金额精度到分
- ✅ 描述信息完整

### 分类规则数据
- ✅ 关键词覆盖率: 80%+
- ✅ 平均置信度: 0.92
- ✅ 规则冲突率: 0%

### 测试覆盖率
- 💰 收入交易: 3条 (19%)
- 💸 支出交易: 13条 (81%)
- 🏷️ 科目覆盖: 12/25个科目 (48%)

## 🎯 验证建议

### 分类准确率测试
1. 上传银行流水数据
2. 运行AI分类
3. 对比`Category`字段和AI输出
4. 计算准确率 = 正确分类数 / 总交易数

### 对账测试
1. 将银行流水拆分为两部分
2. 一部分作为银行记录
3. 另一部分作为账簿记录  
4. 测试自动对账匹配率

### 导出测试
1. 完成分类和对账
2. 导出QuickBooks/Xero格式
3. 在对应软件中测试导入
4. 验证无错误且数据完整

## 🔄 数据更新

如需添加更多测试数据：

1. **银行流水**: 保持字段格式一致，增加不同类型的交易
2. **分类规则**: 添加新的关键词映射，注意避免规则冲突
3. **科目表**: 扩展科目层级，保持代码编号规范
4. **导出模板**: 确保符合目标软件的导入格式要求

---

💡 **提示**: 生产环境使用前，请替换为真实的脱敏数据并调整分类规则。