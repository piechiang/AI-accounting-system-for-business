from typing import Dict, Any, List, Optional
import json
import openai
import anthropic
from app.core.config import settings

class AIService:
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
            self.openai_client = openai
            
        if settings.ANTHROPIC_API_KEY:
            self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def classify_transaction(
        self, 
        transaction: Dict[str, Any], 
        coa_context: List[Dict[str, str]]
    ) -> Optional[Dict[str, Any]]:
        """Classify a transaction using AI"""
        
        # Prepare the prompt
        system_prompt = self._build_classification_prompt(coa_context)
        user_prompt = self._build_transaction_prompt(transaction)
        
        # Try OpenAI first, then Anthropic
        if self.openai_client:
            try:
                return await self._classify_with_openai(system_prompt, user_prompt)
            except Exception as e:
                print(f"OpenAI classification failed: {e}")
        
        if self.anthropic_client:
            try:
                return await self._classify_with_anthropic(system_prompt, user_prompt)
            except Exception as e:
                print(f"Anthropic classification failed: {e}")
        
        return None

    def _build_classification_prompt(self, coa_context: List[Dict[str, str]]) -> str:
        """Build system prompt for classification"""
        coa_list = "\n".join([f"- {coa['code']}: {coa['name']}" for coa in coa_context])
        
        return f"""You are an expert accounting assistant that categorizes business transactions into appropriate Chart of Accounts categories.

Available Chart of Accounts:
{coa_list}

Rules for classification:
1. Choose the most specific and appropriate account category
2. For unclear transactions, choose the most general applicable category
3. Consider the transaction amount, description, and merchant name
4. Return confidence score between 0.0 and 1.0

Return your response as valid JSON in this exact format:
{{
    "coa_code": "account_code",
    "coa_name": "account_name", 
    "confidence": 0.95,
    "reason": "Brief explanation for the classification"
}}"""

    def _build_transaction_prompt(self, transaction: Dict[str, Any]) -> str:
        """Build user prompt with transaction details"""
        return f"""Please classify this business transaction:

Description: {transaction.get('description', 'N/A')}
Merchant/Counterparty: {transaction.get('counterparty', 'N/A')}
Amount: ${transaction.get('amount', 0):,.2f}
Date: {transaction.get('date', 'N/A')}

Classify this transaction into the most appropriate Chart of Accounts category."""

    async def _classify_with_openai(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Classify using OpenAI"""
        try:
            response = await self.openai_client.ChatCompletion.acreate(
                model=settings.DEFAULT_CLASSIFICATION_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            try:
                result = json.loads(content)
                return {
                    'coa_code': result.get('coa_code'),
                    'coa_name': result.get('coa_name'),
                    'confidence': float(result.get('confidence', 0.8)),
                    'reason': result.get('reason', '')
                }
            except json.JSONDecodeError:
                # Try to extract information from free text
                return self._parse_free_text_response(content)
                
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return None

    async def _classify_with_anthropic(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Classify using Anthropic Claude"""
        try:
            message = await self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=200,
                temperature=0.1,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = message.content[0].text.strip()
            
            # Try to parse JSON response
            try:
                result = json.loads(content)
                return {
                    'coa_code': result.get('coa_code'),
                    'coa_name': result.get('coa_name'),
                    'confidence': float(result.get('confidence', 0.8)),
                    'reason': result.get('reason', '')
                }
            except json.JSONDecodeError:
                return self._parse_free_text_response(content)
                
        except Exception as e:
            print(f"Anthropic API error: {e}")
            return None

    def _parse_free_text_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse free text response to extract classification info"""
        import re
        
        # Try to extract account code/name patterns
        code_match = re.search(r'code[:\s]*([0-9]{4})', content, re.IGNORECASE)
        name_match = re.search(r'(?:name|category)[:\s]*([A-Za-z\s&]+)', content, re.IGNORECASE)
        confidence_match = re.search(r'confidence[:\s]*([0-9.]+)', content, re.IGNORECASE)
        
        if code_match or name_match:
            return {
                'coa_code': code_match.group(1) if code_match else None,
                'coa_name': name_match.group(1).strip() if name_match else None,
                'confidence': float(confidence_match.group(1)) if confidence_match else 0.7,
                'reason': 'Parsed from free text response'
            }
        
        return None

    async def analyze_spending_patterns(
        self, 
        transactions: List[Dict[str, Any]], 
        period: str = "monthly"
    ) -> Dict[str, Any]:
        """Analyze spending patterns using AI"""
        
        # Prepare transaction summary
        summary_data = self._prepare_spending_summary(transactions, period)
        
        prompt = f"""Analyze these business spending patterns and provide insights:

{json.dumps(summary_data, indent=2)}

Please provide:
1. Key spending trends and patterns
2. Potential areas of concern or optimization
3. Recommendations for better expense management
4. Any unusual patterns or anomalies detected

Format your response as structured analysis with clear sections."""

        if self.openai_client:
            try:
                response = await self.openai_client.ChatCompletion.acreate(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a financial analyst providing spending pattern insights."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=800
                )
                return {"analysis": response.choices[0].message.content}
            except Exception as e:
                print(f"AI spending analysis failed: {e}")
        
        return {"analysis": "AI analysis not available"}

    def _prepare_spending_summary(self, transactions: List[Dict[str, Any]], period: str) -> Dict[str, Any]:
        """Prepare spending summary for AI analysis"""
        import pandas as pd
        from collections import defaultdict
        
        if not transactions:
            return {}
        
        df = pd.DataFrame(transactions)
        
        # Category breakdown
        category_spending = df.groupby('category')['amount'].sum().to_dict()
        
        # Monthly trends
        df['date'] = pd.to_datetime(df['date'])
        monthly_spending = df.groupby(df['date'].dt.to_period('M'))['amount'].sum().to_dict()
        monthly_spending = {str(k): v for k, v in monthly_spending.items()}
        
        # Top vendors
        vendor_spending = df.groupby('counterparty')['amount'].sum().nlargest(10).to_dict()
        
        return {
            'total_transactions': len(transactions),
            'total_amount': df['amount'].sum(),
            'average_transaction': df['amount'].mean(),
            'period': period,
            'category_breakdown': category_spending,
            'monthly_trends': monthly_spending,
            'top_vendors': vendor_spending,
            'date_range': {
                'start': df['date'].min().isoformat() if not df.empty else None,
                'end': df['date'].max().isoformat() if not df.empty else None
            }
        }

    async def detect_anomalies(
        self, 
        transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect anomalous transactions using AI"""
        
        anomalies = []
        
        # Statistical anomaly detection first
        statistical_anomalies = self._detect_statistical_anomalies(transactions)
        anomalies.extend(statistical_anomalies)
        
        # AI-based pattern analysis for suspicious transactions
        if len(transactions) > 10 and (self.openai_client or self.anthropic_client):
            ai_anomalies = await self._detect_ai_anomalies(transactions)
            anomalies.extend(ai_anomalies)
        
        return anomalies

    def _detect_statistical_anomalies(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect statistical anomalies in transaction amounts"""
        import numpy as np
        
        if len(transactions) < 10:
            return []
        
        amounts = [t['amount'] for t in transactions]
        
        # Use IQR method for outlier detection
        q75, q25 = np.percentile(amounts, [75, 25])
        iqr = q75 - q25
        upper_bound = q75 + 1.5 * iqr
        lower_bound = q25 - 1.5 * iqr
        
        anomalies = []
        for transaction in transactions:
            amount = transaction['amount']
            if amount > upper_bound or amount < lower_bound:
                severity = 'high' if amount > upper_bound * 2 else 'medium'
                anomalies.append({
                    'transaction_id': transaction.get('id'),
                    'anomaly_type': 'amount',
                    'severity': severity,
                    'description': transaction.get('description', ''),
                    'amount': amount,
                    'reason': f'Amount ${amount:,.2f} is outside normal range (${lower_bound:.2f} - ${upper_bound:.2f})'
                })
        
        return anomalies

    async def _detect_ai_anomalies(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use AI to detect pattern-based anomalies"""
        # Implement AI-based anomaly detection
        # This could analyze descriptions, timing patterns, etc.
        # For now, return empty list as placeholder
        return []