#!/usr/bin/env python3
"""
Prompt Manager for TripC.AI Chatbot
Loads and manages prompts from markdown files
"""

import os
import re
from typing import Dict, Optional


class PromptManager:
    """Manages prompts loaded from markdown file"""
    
    def __init__(self, prompt_file_path: str = None):
        if prompt_file_path is None:
            # Default path relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_file_path = os.path.join(current_dir, "prompts.md")
        
        self.prompt_file_path = prompt_file_path
        self.prompts = self._load_prompts()
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load prompts from markdown file"""
        prompts = {}
        
        try:
            if os.path.exists(self.prompt_file_path):
                with open(self.prompt_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract all prompt sections using regex
                # Look for ### headers followed by code blocks
                sections = re.findall(r'### ([^\n]+)\s*```(.*?)```', content, re.DOTALL)
                
                for header, prompt_content in sections:
                    # Clean up header and create key
                    header_clean = header.strip().lower().replace(' ', '_')
                    prompt_clean = prompt_content.strip()
                    
                    # Map common headers to standard keys
                    if 'vietnamese' in header_clean and 'intent' in header_clean and 'system' in header_clean:
                        key = 'vi_intent_system'
                    elif 'english' in header_clean and 'intent' in header_clean and 'system' in header_clean:
                        key = 'en_intent_system'
                    elif 'vietnamese' in header_clean and 'user' in header_clean and 'template' in header_clean:
                        key = 'vi_intent_user_template'
                    elif 'english' in header_clean and 'user' in header_clean and 'template' in header_clean:
                        key = 'en_intent_user_template'
                    elif 'vietnamese' in header_clean and 'service' in header_clean:
                        key = 'vi_service_system'
                    elif 'english' in header_clean and 'service' in header_clean:
                        key = 'en_service_system'
                    elif 'vietnamese' in header_clean and 'qna' in header_clean:
                        key = 'vi_qna_system'
                    elif 'english' in header_clean and 'qna' in header_clean:
                        key = 'en_qna_system'
                    else:
                        # For other prompts, create a generic key
                        key = header_clean
                    
                    prompts[key] = prompt_clean
                
                print(f"✅ Loaded {len(prompts)} prompts from {self.prompt_file_path}")
                print(f"📝 Available prompts: {list(prompts.keys())}")
            else:
                print(f"⚠️ Prompt file not found: {self.prompt_file_path}")
                
        except Exception as e:
            print(f"❌ Error loading prompts: {e}")
        
        return prompts
    
    def get_intent_system_prompt(self, language: str = "vi") -> str:
        """Get system prompt for intent classification"""
        key = f"{language}_intent_system"
        return self.prompts.get(key, self.prompts.get('en_intent_system', ''))
    
    def get_intent_user_template(self, language: str = "vi") -> str:
        """Get user prompt template for intent classification"""
        key = f"{language}_intent_user_template"
        return self.prompts.get(key, self.prompts.get('en_intent_user_template', ''))
    
    def get_service_system_prompt(self, language: str = "vi") -> str:
        """Get system prompt for service agent"""
        key = f"{language}_service_system"
        return self.prompts.get(key, self.prompts.get('en_service_system', ''))
    
    def get_qna_system_prompt(self, language: str = "vi") -> str:
        """Get system prompt for QnA agent"""
        key = f"{language}_qna_system"
        return self.prompts.get(key, self.prompts.get('en_qna_system', ''))
    
    def get_prompt(self, key: str) -> str:
        """Get prompt by key"""
        return self.prompts.get(key, '')
    
    def list_available_prompts(self) -> list:
        """List all available prompt keys"""
        return list(self.prompts.keys())
    
    def reload_prompts(self):
        """Reload prompts from file (useful for hot-reloading during development)"""
        print("🔄 Reloading prompts...")
        self.prompts = self._load_prompts()
        return self.prompts
    
    def validate_prompts(self) -> Dict[str, bool]:
        """Validate that all required prompts are loaded"""
        required_prompts = [
            'vi_intent_system', 'en_intent_system',
            'vi_intent_user_template', 'en_intent_user_template'
        ]
        
        validation = {}
        for prompt in required_prompts:
            validation[prompt] = prompt in self.prompts
        
        return validation
