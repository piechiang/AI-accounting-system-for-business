"""
AI service for LLM-based transaction classification with strict JSON validation.
Provides fallback classification when rules and embeddings fail.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List
import hashlib
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class AIService:
    """Service for LLM-based transaction classification."""
    
    def __init__(self):
        self.cache = {}
        self.retry_attempts = 3
        self.retry_delay = 1.0  # seconds
        self.cache_ttl = timedelta(hours=1)
        
        # Expected JSON schema for LLM responses
        self.response_schema = {
            "type": "object",
            "required": ["coa_code", "confidence", "reason"],
            "properties": {
                "coa_code": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "reason": {"type": "string", "minLength": 10}
            }
        }
    
    def _generate_cache_key(self, description: str, amount: float, vendor: str) -> str:
        """
        Generate cache key for transaction classification.
        
        Args:
            description: Transaction description
            amount: Transaction amount
            vendor: Vendor/counterparty name
            
        Returns:
            Hash-based cache key
        """
        cache_input = f"{description}|{amount}|{vendor}".lower()
        return hashlib.sha256(cache_input.encode()).hexdigest()[:16]
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached classification result.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached result or None if not found/expired
        """
        if cache_key in self.cache:
            cached_entry = self.cache[cache_key]
            
            # Check if cache entry is still valid
            if datetime.now() - cached_entry['timestamp'] < self.cache_ttl:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_entry['result']
            else:
                # Remove expired entry
                del self.cache[cache_key]
                logger.debug(f"Cache expired for key: {cache_key}")
        
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """
        Cache classification result.
        
        Args:
            cache_key: Cache key
            result: Result to cache
        """
        self.cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }
        
        # Clean old cache entries periodically
        if len(self.cache) > 1000:  # Max 1000 entries
            self._clean_cache()
    
    def _clean_cache(self):
        """Remove expired cache entries."""
        cutoff_time = datetime.now() - self.cache_ttl
        expired_keys = [
            k for k, v in self.cache.items()
            if v['timestamp'] < cutoff_time
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        logger.info(f"Cleaned {len(expired_keys)} expired cache entries")
    
    def _validate_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Validate and parse LLM JSON response.
        
        Args:
            response_text: Raw LLM response text
            
        Returns:
            Parsed and validated JSON or None if invalid
        """
        try:
            # Try to extract JSON from response (handles cases where LLM adds extra text)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in LLM response")
                return None
            
            json_str = json_match.group(0)
            parsed_json = json.loads(json_str)
            
            # Validate required fields
            required_fields = ["coa_code", "confidence", "reason"]
            for field in required_fields:
                if field not in parsed_json:
                    logger.warning(f"Missing required field: {field}")
                    return None
            
            # Validate data types and ranges
            if not isinstance(parsed_json["coa_code"], str):
                logger.warning("coa_code must be string")
                return None
            
            if not isinstance(parsed_json["confidence"], (int, float)):
                logger.warning("confidence must be number")
                return None
            
            confidence = float(parsed_json["confidence"])
            if not (0.0 <= confidence <= 1.0):
                logger.warning(f"confidence must be between 0.0 and 1.0, got: {confidence}")
                return None
            
            if not isinstance(parsed_json["reason"], str) or len(parsed_json["reason"]) < 10:
                logger.warning("reason must be string with at least 10 characters")
                return None
            
            # Normalize confidence to ensure it's a float
            parsed_json["confidence"] = confidence
            
            return parsed_json
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in LLM response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error validating LLM response: {e}")
            return None
    
    def _call_llm_api(self, prompt: str) -> Optional[str]:
        """
        Make API call to LLM service.
        
        Args:
            prompt: Formatted prompt for classification
            
        Returns:
            Raw LLM response or None if failed
        """
        # TODO: Replace with actual LLM API call (OpenAI, Anthropic, etc.)
        # For now, return a mock response for testing
        
        try:
            # Mock LLM response that follows the expected JSON schema
            mock_response = {
                "coa_code": "5100",
                "confidence": 0.82,
                "reason": "This transaction appears to be an office supply purchase based on the vendor name and typical business expense patterns."
            }
            
            return json.dumps(mock_response)
            
        except Exception as e:
            logger.error(f"Error calling LLM API: {e}")
            return None
    
    def _build_classification_prompt(
        self, 
        transaction_context: Dict[str, Any], 
        coa_options: List[Dict[str, str]]
    ) -> str:
        """
        Build prompt for LLM classification.
        
        Args:
            transaction_context: Transaction details
            coa_options: Available chart of accounts options
            
        Returns:
            Formatted prompt string
        """
        coa_list = "\n".join([
            f"- {coa['code']}: {coa['name']}" 
            for coa in coa_options[:20]  # Limit to top 20 for prompt length
        ])
        
        prompt = f"""You are an expert accounting AI assistant. Classify this business transaction into the most appropriate Chart of Accounts category.

Transaction Details:
- Description: {transaction_context.get('description', 'N/A')}
- Vendor/Counterparty: {transaction_context.get('counterparty', 'N/A')}
- Amount: ${transaction_context.get('amount', 0):.2f}
- Date: {transaction_context.get('date', 'N/A')}

Available Chart of Accounts:
{coa_list}

IMPORTANT: You must respond with ONLY a valid JSON object in this exact format:
{{
    "coa_code": "XXXX",
    "confidence": 0.XX,
    "reason": "Brief explanation of why this classification was chosen"
}}

Requirements:
- coa_code: Must exactly match one of the codes listed above
- confidence: Number between 0.0 and 1.0 indicating certainty
- reason: At least 10 characters explaining the classification logic

Do not include any text before or after the JSON object."""

        return prompt
    
    async def classify_transaction(
        self, 
        transaction_context: Dict[str, Any], 
        coa_options: List[Dict[str, str]]
    ) -> Optional[Dict[str, Any]]:
        """
        Classify transaction using LLM with retry logic and caching.
        
        Args:
            transaction_context: Transaction details (description, amount, etc.)
            coa_options: Available chart of accounts options
            
        Returns:
            Classification result or None if failed
        """
        # Generate cache key
        description = transaction_context.get('description', '')
        amount = transaction_context.get('amount', 0.0)
        vendor = transaction_context.get('counterparty', '')
        cache_key = self._generate_cache_key(description, amount, vendor)
        
        # Check cache first
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Build prompt
        prompt = self._build_classification_prompt(transaction_context, coa_options)
        
        # Retry logic with exponential backoff
        for attempt in range(self.retry_attempts):
            try:
                logger.debug(f"LLM classification attempt {attempt + 1}/{self.retry_attempts}")
                
                # Call LLM API
                raw_response = self._call_llm_api(prompt)
                if not raw_response:
                    raise Exception("No response from LLM API")
                
                # Validate and parse response
                parsed_response = self._validate_json_response(raw_response)
                if not parsed_response:
                    raise Exception("Invalid JSON response from LLM")
                
                # Map coa_code to actual COA ID (this would be done by calling service)
                result = {
                    'coa_code': parsed_response['coa_code'],
                    'coa_name': self._get_coa_name_by_code(parsed_response['coa_code'], coa_options),
                    'confidence': parsed_response['confidence'],
                    'reason': parsed_response['reason'],
                    'method': 'llm',
                    'cache_key': cache_key
                }
                
                # Cache successful result
                self._cache_result(cache_key, result)
                
                logger.info(f"LLM classification successful on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                logger.warning(f"LLM classification attempt {attempt + 1} failed: {e}")
                
                if attempt < self.retry_attempts - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    logger.debug(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.retry_attempts} LLM classification attempts failed")
        
        return None
    
    def _get_coa_name_by_code(self, coa_code: str, coa_options: List[Dict[str, str]]) -> str:
        """
        Get COA name by code from available options.
        
        Args:
            coa_code: COA code to lookup
            coa_options: Available COA options
            
        Returns:
            COA name or 'Unknown' if not found
        """
        for coa in coa_options:
            if coa['code'] == coa_code:
                return coa['name']
        return 'Unknown'
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.
        
        Returns:
            Cache statistics
        """
        total_entries = len(self.cache)
        expired_count = 0
        cutoff_time = datetime.now() - self.cache_ttl
        
        for entry in self.cache.values():
            if entry['timestamp'] < cutoff_time:
                expired_count += 1
        
        return {
            'total_entries': total_entries,
            'expired_entries': expired_count,
            'active_entries': total_entries - expired_count,
            'cache_ttl_hours': self.cache_ttl.total_seconds() / 3600,
            'retry_attempts': self.retry_attempts
        }
    
    def clear_cache(self):
        """Clear all cached results."""
        self.cache.clear()
        logger.info("AI service cache cleared")

# TODO: Implement actual LLM API integration:
#
# Example for OpenAI:
# import openai
# 
# def _call_openai_api(self, prompt: str) -> Optional[str]:
#     try:
#         response = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.1,
#             max_tokens=500
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         logger.error(f"OpenAI API error: {e}")
#         return None
#
# Example for Anthropic:
# import anthropic
#
# def _call_anthropic_api(self, prompt: str) -> Optional[str]:
#     try:
#         client = anthropic.Anthropic()
#         response = client.messages.create(
#             model="claude-3-haiku-20240307",
#             max_tokens=500,
#             temperature=0.1,
#             messages=[{"role": "user", "content": prompt}]
#         )
#         return response.content[0].text
#     except Exception as e:
#         logger.error(f"Anthropic API error: {e}")
#         return None