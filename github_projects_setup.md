# 🚀 GitHub Projects Setup Guide

## 创建项目看板

### 1. 在GitHub仓库中创建Projects
```
Repository → Projects → New Project → Board Template
```

### 2. 设置看板列（Columns）
- **📝 Backlog** - 待规划任务
- **🔄 Ready** - 已准备开始
- **🏗️ In Progress** - 进行中
- **👀 Code Review** - 代码审查
- **🧪 QA Testing** - 质量验证
- **✅ Done** - 已完成

### 3. 设置标签（Labels）
- `priority: critical` 🔴
- `priority: high` 🟠  
- `priority: medium` 🟡
- `priority: low` 🟢
- `type: feature` 💫
- `type: bug` 🐛
- `type: enhancement` ⚡
- `area: backend` 🔧
- `area: frontend` 🎨
- `area: tax-engine` 🏛️
- `area: testing` 🧪
- `milestone: M1` 📅
- `milestone: M2` 📅
- ...等

## Week 1 详细任务分解

### Epic 1: Enhanced Data Models & Migration
**Estimated Time**: 16 hours

#### Issue #1: Extend Transaction Models
```markdown
**Title**: Extend transaction models for tax compliance

**Description**:
Enhance existing transaction and COA models to support tax categorization and multi-entity scenarios.

**Acceptance Criteria**:
- [ ] Add `tax_category` field to ChartOfAccounts model
- [ ] Create TaxMapping model for 1120/1120S/1065 forms
- [ ] Add `entity_type` support (C-Corp, S-Corp, Partnership)
- [ ] Create database migration scripts
- [ ] Update model relationships and foreign keys

**Technical Notes**:
- Extend `app/models/accounts.py`
- Create `app/models/tax_mappings.py`  
- Add Alembic migration
- Update schemas in `app/schemas/`

**Definition of Done**:
- [ ] All models pass validation tests
- [ ] Migration runs successfully on fresh DB
- [ ] API endpoints return updated schema
- [ ] Backward compatibility maintained

**Labels**: `type: feature`, `area: backend`, `milestone: M1`, `priority: critical`
**Assignee**: Backend Developer
**Estimated Hours**: 6
```

#### Issue #2: Tax Mapping Data Structure
```markdown
**Title**: Create comprehensive tax mapping data structure

**Description**:
Build the data structure that maps Chart of Accounts to specific tax form lines for different entity types.

**Acceptance Criteria**:
- [ ] Create tax_mapping_1120.csv with complete line mappings
- [ ] Create tax_mapping_1120s.csv for S-Corp specifics
- [ ] Create tax_mapping_1065.csv for Partnership forms
- [ ] Add validation for mapping consistency
- [ ] Create data loading scripts

**Files to Create**:
- `datasets/tax_mappings/mapping_1120.csv`
- `datasets/tax_mappings/mapping_1120s.csv`
- `datasets/tax_mappings/mapping_1065.csv`
- `scripts/load_tax_mappings.py`

**Definition of Done**:
- [ ] Mappings cover 95%+ of common COA accounts
- [ ] Data loads without errors
- [ ] Validation scripts pass all checks
- [ ] Documentation explains mapping logic

**Labels**: `type: feature`, `area: tax-engine`, `milestone: M1`, `priority: high`
**Estimated Hours**: 8
```

### Epic 2: Advanced Data Ingestion
**Estimated Time**: 20 hours

#### Issue #3: Multi-Format Data Importer
```markdown
**Title**: Build enterprise-grade data import system

**Description**:
Enhance the existing CSV importer to handle multiple formats and provide detailed validation feedback.

**Acceptance Criteria**:
- [ ] Support CSV, Excel (.xlsx), QBO export format
- [ ] Add field mapping interface for unknown formats
- [ ] Implement data quality scoring
- [ ] Add duplicate detection algorithms
- [ ] Create import preview with validation results

**Technical Implementation**:
- Extend `app/services/data_cleaning_service.py`
- Add pandas Excel support
- Create format detection logic
- Add validation dashboard endpoint

**Definition of Done**:
- [ ] Import 10K+ transactions in <30 seconds
- [ ] Support at least 5 different bank formats
- [ ] Duplicate detection accuracy >99%
- [ ] User-friendly error reporting

**Labels**: `type: enhancement`, `area: backend`, `milestone: M1`, `priority: high`
**Estimated Hours**: 12
```

#### Issue #4: Advanced Data Validation
```markdown
**Title**: Implement comprehensive data validation framework

**Description**:
Build robust validation system that catches data quality issues before they affect downstream processing.

**Acceptance Criteria**:
- [ ] Date format validation and normalization
- [ ] Currency amount validation (handle negative values, formatting)
- [ ] Description text cleaning (remove special chars, normalize)
- [ ] Account code validation against COA
- [ ] Statistical outlier detection

**Technical Notes**:
```python
class DataValidator:
    def validate_transaction_batch(self, transactions: List[Dict]) -> ValidationReport
    def detect_outliers(self, amounts: List[float]) -> List[int]
    def normalize_descriptions(self, descriptions: List[str]) -> List[str]
    def validate_date_formats(self, dates: List[str]) -> List[bool]
```

**Definition of Done**:
- [ ] Validation covers all critical fields
- [ ] Performance: 1000 transactions/second
- [ ] Clear error messages for users
- [ ] Configurable validation rules

**Labels**: `type: feature`, `area: backend`, `milestone: M1`, `priority: medium`
**Estimated Hours**: 8
```

### Epic 3: Hybrid Classification System
**Estimated Time**: 24 hours

#### Issue #5: Enhanced Rule Engine
```markdown
**Title**: Build self-learning classification rule engine

**Description**:
Enhance the existing rule-based classification with machine learning feedback and confidence scoring.

**Acceptance Criteria**:
- [ ] Support complex regex patterns with priority
- [ ] Add merchant name matching with fuzzy logic
- [ ] Implement rule learning from human corrections
- [ ] Add confidence scoring for rule matches
- [ ] Create rule conflict resolution

**Technical Architecture**:
```python
class EnhancedClassificationService:
    def classify_with_rules(self, transaction: Dict) -> ClassificationResult
    def learn_from_correction(self, transaction_id: int, correct_category: str)
    def resolve_rule_conflicts(self, matches: List[RuleMatch]) -> RuleMatch
    def calculate_confidence(self, match: RuleMatch) -> float
```

**Definition of Done**:
- [ ] Rule classification accuracy >92%
- [ ] Learning improves accuracy over time
- [ ] Rule conflicts handled gracefully
- [ ] Performance: <100ms per transaction

**Labels**: `type: enhancement`, `area: backend`, `milestone: M1`, `priority: critical`
**Estimated Hours**: 10
```

#### Issue #6: LLM Integration & Fallback
```markdown
**Title**: Integrate LLM classification with smart fallback

**Description**:
Add LLM-powered classification as fallback for transactions that don't match rules, with cost optimization.

**Acceptance Criteria**:
- [ ] OpenAI/Anthropic API integration with retries
- [ ] Batch processing for cost efficiency
- [ ] Response caching to avoid duplicate calls
- [ ] Fallback chain: Rules → LLM → Manual
- [ ] Cost monitoring and budget controls

**API Design**:
```python
class LLMClassificationService:
    def classify_batch(self, transactions: List[Dict]) -> List[ClassificationResult]
    def get_explanation(self, transaction: Dict, category: str) -> str
    def estimate_cost(self, transaction_count: int) -> float
    def check_budget_limit(self) -> bool
```

**Definition of Done**:
- [ ] LLM accuracy >90% on rule failures
- [ ] Cost per transaction <$0.001
- [ ] Response time <2 seconds for batches of 50
- [ ] Graceful degradation when APIs unavailable

**Labels**: `type: feature`, `area: backend`, `milestone: M1`, `priority: high`
**Estimated Hours**: 14
```

### Epic 4: Frontend Enhancements
**Estimated Time**: 12 hours

#### Issue #7: Enhanced Transaction Management UI
```markdown
**Title**: Build professional transaction review interface

**Description**:
Create intuitive interface for reviewing and correcting AI classifications.

**Acceptance Criteria**:
- [ ] Data table with sorting, filtering, pagination
- [ ] Inline editing for category corrections
- [ ] Bulk actions (approve, reject, reclassify)
- [ ] Confidence indicators and explanations
- [ ] Real-time learning feedback

**UI Components**:
- Advanced DataTable with selection
- Classification confidence badges
- Category dropdown with search
- Bulk action toolbar
- Progress indicators

**Definition of Done**:
- [ ] Handle 10K+ transactions smoothly
- [ ] Mobile-responsive design
- [ ] Keyboard shortcuts for power users
- [ ] Real-time updates without page refresh

**Labels**: `type: feature`, `area: frontend`, `milestone: M1`, `priority: medium`
**Estimated Hours**: 12
```

## Week 1 Sprint Planning

### Daily Standup Template
```
Yesterday:
- What did you complete?
- Any blockers encountered?

Today:
- What will you work on?
- Expected completion time?

Blockers:
- What do you need help with?
- Dependencies waiting on others?
```

### Sprint Metrics
- **Velocity Target**: 40 story points (80 hours total)
- **Team Capacity**: 2 developers × 40 hours = 80 hours
- **Buffer**: 20% for unexpected issues
- **Daily Progress Reviews**: 15-minute daily standups

### End of Week 1 Demo
**Demo Script** (15 minutes):
1. **Data Import** (3 min): Show multi-format upload with validation
2. **Rule Classification** (4 min): Demonstrate rule matching and learning
3. **LLM Fallback** (3 min): Show AI classification for complex cases
4. **Human Review** (3 min): Correction interface and feedback loop
5. **Metrics Dashboard** (2 min): Show accuracy and performance stats

### Success Criteria for M1
- [ ] All Epic acceptance criteria met
- [ ] End-to-end demo successful
- [ ] Performance benchmarks achieved
- [ ] Code review completed
- [ ] Unit tests >80% coverage
- [ ] Documentation updated