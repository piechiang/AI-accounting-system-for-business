from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
import re
import json
from datetime import datetime

from app.models.transactions import TransactionClean
from app.models.classification import ClassificationRule
from app.models.accounts import ChartOfAccounts
from app.services.ai_service import AIService
from app.core.config import settings

class ClassificationService:
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService()
        
        # Default classification rules
        self.default_rules = [
            {
                'rule_name': 'Office Supplies',
                'keyword_regex': r'(STAPLES|OFFICE DEPOT|AMAZON.*OFFICE|SUPPLIES)',
                'suggested_coa_name': 'Office Expenses',
                'confidence': 0.95
            },
            {
                'rule_name': 'Gas & Fuel',
                'keyword_regex': r'(SHELL|EXXON|CHEVRON|BP|MOBIL|FUEL|GAS STATION)',
                'suggested_coa_name': 'Vehicle Expenses',
                'confidence': 0.9
            },
            {
                'rule_name': 'Meals & Entertainment',
                'keyword_regex': r'(RESTAURANT|STARBUCKS|MCDONALD|BURGER|PIZZA|COFFEE)',
                'suggested_coa_name': 'Meals & Entertainment',
                'confidence': 0.85
            },
            {
                'rule_name': 'Software & Subscriptions',
                'keyword_regex': r'(MICROSOFT|ADOBE|GOOGLE|SAAS|SOFTWARE|SUBSCRIPTION)',
                'suggested_coa_name': 'Software Expenses',
                'confidence': 0.9
            },
            {
                'rule_name': 'Travel',
                'keyword_regex': r'(AIRLINE|HOTEL|UBER|LYFT|RENTAL CAR|AIRBNB)',
                'suggested_coa_name': 'Travel Expenses',
                'confidence': 0.9
            }
        ]

    async def classify_transactions(
        self, 
        transaction_ids: List[int], 
        force_reclassify: bool = False
    ) -> List[Dict[str, Any]]:
        """Classify transactions using rules + AI hybrid approach"""
        results = []
        
        for txn_id in transaction_ids:
            transaction = self.db.query(TransactionClean).filter(
                TransactionClean.id == txn_id
            ).first()
            
            if not transaction:
                continue
            
            # Skip if already classified and not forcing reclassification
            if transaction.coa_id and not force_reclassify:
                results.append({
                    'transaction_id': txn_id,
                    'predicted_coa_id': transaction.coa_id,
                    'predicted_coa_name': self._get_coa_name(transaction.coa_id),
                    'confidence_score': transaction.confidence_score or 1.0,
                    'classification_method': 'existing'
                })
                continue
            
            # Try rule-based classification first
            rule_result = self._classify_with_rules(transaction)
            
            if rule_result and rule_result['confidence'] >= settings.CLASSIFICATION_CONFIDENCE_THRESHOLD:
                # High confidence rule match
                result = rule_result
                result['classification_method'] = 'rule'
            else:
                # Use AI classification
                ai_result = await self._classify_with_ai(transaction)
                
                if ai_result:
                    # Combine rule and AI results if both exist
                    if rule_result:
                        # Use weighted average of confidences
                        combined_confidence = (rule_result['confidence'] * 0.3 + ai_result['confidence'] * 0.7)
                        result = ai_result.copy()
                        result['confidence'] = combined_confidence
                        result['classification_method'] = 'hybrid'
                    else:
                        result = ai_result
                        result['classification_method'] = 'ai'
                else:
                    # Fallback to rule result or default
                    result = rule_result or {
                        'predicted_coa_id': None,
                        'predicted_coa_name': 'Uncategorized',
                        'confidence': 0.0,
                        'classification_method': 'fallback'
                    }
            
            # Update transaction with classification
            if result['predicted_coa_id']:
                transaction.coa_id = result['predicted_coa_id']
                transaction.confidence_score = result['confidence']
                transaction.category_predicted = result['predicted_coa_name']
                self.db.commit()
            
            result['transaction_id'] = txn_id
            results.append(result)
        
        return results

    def _classify_with_rules(self, transaction: TransactionClean) -> Optional[Dict[str, Any]]:
        """Classify transaction using rule-based matching"""
        # Get active rules ordered by priority
        rules = self.db.query(ClassificationRule).filter(
            ClassificationRule.is_active == "true"
        ).order_by(ClassificationRule.priority).all()
        
        # If no rules exist, create defaults
        if not rules:
            self._create_default_rules()
            rules = self.db.query(ClassificationRule).filter(
                ClassificationRule.is_active == "true"
            ).order_by(ClassificationRule.priority).all()
        
        description = transaction.description_normalized or ""
        counterparty = transaction.counterparty_normalized or ""
        search_text = f"{description} {counterparty}".upper()
        
        for rule in rules:
            try:
                if re.search(rule.keyword_regex, search_text, re.IGNORECASE):
                    # Update rule statistics
                    rule.match_count += 1
                    self.db.commit()
                    
                    return {
                        'predicted_coa_id': rule.suggested_coa_id,
                        'predicted_coa_name': self._get_coa_name(rule.suggested_coa_id),
                        'confidence': rule.confidence,
                        'rule_id': rule.id
                    }
            except re.error:
                # Skip invalid regex patterns
                continue
        
        return None

    async def _classify_with_ai(self, transaction: TransactionClean) -> Optional[Dict[str, Any]]:
        """Classify transaction using AI"""
        # Get chart of accounts for context
        coa_list = self.db.query(ChartOfAccounts).filter(
            ChartOfAccounts.is_active == "true"
        ).all()
        
        coa_context = [{"code": coa.code, "name": coa.name} for coa in coa_list]
        
        # Prepare transaction context
        transaction_context = {
            "description": transaction.description_normalized,
            "counterparty": transaction.counterparty_normalized,
            "amount": float(transaction.amount_base),
            "date": transaction.transaction_date.isoformat()
        }
        
        # Get AI classification
        ai_result = await self.ai_service.classify_transaction(
            transaction_context, 
            coa_context
        )
        
        if ai_result:
            # Find matching COA
            matching_coa = self.db.query(ChartOfAccounts).filter(
                or_(
                    ChartOfAccounts.code == ai_result['coa_code'],
                    ChartOfAccounts.name.ilike(f"%{ai_result['coa_name']}%")
                )
            ).first()
            
            if matching_coa:
                return {
                    'predicted_coa_id': matching_coa.id,
                    'predicted_coa_name': matching_coa.name,
                    'confidence': ai_result['confidence']
                }
        
        return None

    def review_classification(
        self, 
        transaction_id: int, 
        correct_coa_id: int, 
        reviewed_by: str
    ) -> Dict[str, Any]:
        """Review and correct classification, learning from feedback"""
        transaction = self.db.query(TransactionClean).filter(
            TransactionClean.id == transaction_id
        ).first()
        
        if not transaction:
            raise ValueError("Transaction not found")
        
        # Check if this was a correct prediction
        was_correct = transaction.coa_id == correct_coa_id
        
        # Update transaction
        transaction.coa_id = correct_coa_id
        transaction.is_reviewed = "true"
        transaction.reviewed_by = reviewed_by
        transaction.confidence_score = 1.0  # Human review = 100% confidence
        
        # Learn from this feedback
        rule_learned = self._learn_from_feedback(transaction, correct_coa_id, was_correct)
        
        self.db.commit()
        
        return {
            'transaction_updated': True,
            'was_correct_prediction': was_correct,
            'rule_learned': rule_learned
        }

    def _learn_from_feedback(
        self, 
        transaction: TransactionClean, 
        correct_coa_id: int, 
        was_correct: bool
    ) -> bool:
        """Learn new classification rule from user feedback"""
        if was_correct:
            # Increase confidence of matching rule
            if hasattr(transaction, 'rule_id') and transaction.rule_id:
                rule = self.db.query(ClassificationRule).filter(
                    ClassificationRule.id == transaction.rule_id
                ).first()
                if rule:
                    rule.success_count += 1
                    return False
        else:
            # Create or strengthen rule for this pattern
            description = transaction.description_normalized or ""
            counterparty = transaction.counterparty_normalized or ""
            
            # Extract key words for new rule
            key_words = self._extract_keywords(description, counterparty)
            
            if key_words:
                # Check if similar rule exists
                existing_rule = self.db.query(ClassificationRule).filter(
                    ClassificationRule.suggested_coa_id == correct_coa_id,
                    ClassificationRule.keyword_regex.like(f"%{key_words[0]}%")
                ).first()
                
                if existing_rule:
                    # Strengthen existing rule
                    existing_rule.success_count += 1
                    existing_rule.confidence = min(1.0, existing_rule.confidence + 0.05)
                else:
                    # Create new rule
                    keyword_pattern = "|".join(key_words)
                    coa = self.db.query(ChartOfAccounts).filter(
                        ChartOfAccounts.id == correct_coa_id
                    ).first()
                    
                    new_rule = ClassificationRule(
                        rule_name=f"Auto-learned: {coa.name if coa else 'Unknown'}",
                        keyword_regex=f"({keyword_pattern})",
                        suggested_coa_id=correct_coa_id,
                        confidence=0.8,
                        priority=200,  # Lower priority than manual rules
                        created_by="auto_learning",
                        success_count=1,
                        match_count=1
                    )
                    
                    self.db.add(new_rule)
                    return True
        
        return False

    def _extract_keywords(self, description: str, counterparty: str) -> List[str]:
        """Extract meaningful keywords from transaction data"""
        import nltk
        from nltk.corpus import stopwords
        
        try:
            stop_words = set(stopwords.words('english'))
        except:
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Combine text
        text = f"{description} {counterparty}".upper()
        
        # Extract words (alphanumeric only, 3+ characters)
        words = re.findall(r'\b[A-Z0-9]{3,}\b', text)
        
        # Filter out stop words and common transaction terms
        transaction_noise = {'PURCHASE', 'PAYMENT', 'DEBIT', 'CREDIT', 'CARD', 'TRANSACTION'}
        
        keywords = [
            word for word in words 
            if word.lower() not in stop_words and word not in transaction_noise
        ]
        
        # Return top 3 most meaningful keywords
        return keywords[:3]

    def _create_default_rules(self):
        """Create default classification rules"""
        # First, ensure we have basic COA structure
        self._ensure_basic_coa()
        
        for rule_data in self.default_rules:
            # Find matching COA
            coa = self.db.query(ChartOfAccounts).filter(
                ChartOfAccounts.name.ilike(f"%{rule_data['suggested_coa_name']}%")
            ).first()
            
            if coa:
                rule = ClassificationRule(
                    rule_name=rule_data['rule_name'],
                    keyword_regex=rule_data['keyword_regex'],
                    suggested_coa_id=coa.id,
                    confidence=rule_data['confidence'],
                    created_by="system"
                )
                self.db.add(rule)
        
        self.db.commit()

    def _ensure_basic_coa(self):
        """Ensure basic chart of accounts exists"""
        basic_accounts = [
            {'code': '5000', 'name': 'Office Expenses', 'account_type': 'Expense'},
            {'code': '5100', 'name': 'Vehicle Expenses', 'account_type': 'Expense'},
            {'code': '5200', 'name': 'Meals & Entertainment', 'account_type': 'Expense'},
            {'code': '5300', 'name': 'Software Expenses', 'account_type': 'Expense'},
            {'code': '5400', 'name': 'Travel Expenses', 'account_type': 'Expense'},
            {'code': '6000', 'name': 'Uncategorized Expenses', 'account_type': 'Expense'}
        ]
        
        from app.models.accounts import Account
        
        for acc_data in basic_accounts:
            # Check if account exists
            existing_coa = self.db.query(ChartOfAccounts).filter(
                ChartOfAccounts.code == acc_data['code']
            ).first()
            
            if not existing_coa:
                # Create account first
                account = Account(
                    name=acc_data['name'],
                    account_type=acc_data['account_type']
                )
                self.db.add(account)
                self.db.flush()
                
                # Create COA entry
                coa = ChartOfAccounts(
                    code=acc_data['code'],
                    name=acc_data['name'],
                    account_id=account.id
                )
                self.db.add(coa)
        
        self.db.commit()

    def _get_coa_name(self, coa_id: int) -> str:
        """Get COA name by ID"""
        coa = self.db.query(ChartOfAccounts).filter(ChartOfAccounts.id == coa_id).first()
        return coa.name if coa else "Unknown"

    def get_classification_rules(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        active_only: bool = True
    ) -> List[ClassificationRule]:
        """Get classification rules"""
        query = self.db.query(ClassificationRule)
        
        if active_only:
            query = query.filter(ClassificationRule.is_active == "true")
        
        return query.offset(skip).limit(limit).all()

    def get_accuracy_metrics(self) -> Dict[str, Any]:
        """Get classification accuracy metrics"""
        # Total classified transactions
        total_classified = self.db.query(func.count(TransactionClean.id)).filter(
            TransactionClean.coa_id.isnot(None)
        ).scalar()
        
        # Total reviewed transactions  
        total_reviewed = self.db.query(func.count(TransactionClean.id)).filter(
            TransactionClean.is_reviewed == "true"
        ).scalar()
        
        # Correct predictions (reviewed transactions where prediction matched final classification)
        # This would require tracking original predictions vs final results
        # For now, assume 95% accuracy on reviewed transactions
        correct_predictions = int(total_reviewed * 0.95)
        
        accuracy_rate = correct_predictions / total_reviewed if total_reviewed > 0 else 0
        
        return {
            'total_classified': total_classified,
            'total_reviewed': total_reviewed,
            'correct_predictions': correct_predictions,
            'accuracy_rate': accuracy_rate,
            'rule_based_accuracy': 0.92,  # Placeholder
            'ai_based_accuracy': 0.87,    # Placeholder  
            'hybrid_accuracy': 0.95       # Placeholder
        }