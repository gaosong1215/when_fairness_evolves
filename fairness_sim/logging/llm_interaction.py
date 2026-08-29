# -*- coding: utf-8 -*-
"""
llm_interaction_logger.py

Real-time LLM interaction logging tool
Records input and output of each LLM call during experiment execution
"""

import csv
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List


class LLMInteractionLogger:
    """LLM interaction logger"""
    
    def __init__(self, log_dir: str = "llm_logs", experiment_id: str = None):
        """
        Initialize logger
        
        Args:
            log_dir: Log save directory
            experiment_id: Experiment ID, auto-generated if None
        """
        self.log_dir = log_dir
        
        # Create log directory
        os.makedirs(log_dir, exist_ok=True)
        
        # Generate experiment ID
        if experiment_id is None:
            experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.experiment_id = experiment_id
        
        # CSV file path
        self.csv_file = os.path.join(log_dir, f"llm_interactions_{experiment_id}.csv")
        
        # Initialize CSV file
        self._init_csv()
        
        # Statistics
        self.total_calls = 0
        self.calls_by_round = {}
        
        print(f"📝 LLM interaction logger started")
        print(f"   Log file: {self.csv_file}")
    
    def _init_csv(self):
        """Initialize CSV file and write header"""
        with open(self.csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Timestamp',
                'Round_Number',
                'Agent_ID',
                'Family_Name',
                'Value_Type',
                'Members',
                'Labor_Force',
                'Distribution_Method',
                'Allocated_Resources',
                'Call_Type',
                'LLM_Model',
                'Temperature',
                'LLM_Input_Prompt',
                'LLM_Raw_Output',
                'Extracted_Score',
                'Processed_Data',
                'Duration_Seconds',
                'Success'
            ])
    
    def log_evaluation_call(
        self,
        round_number: int,
        agent: Dict[str, Any],
        distribution_method: str,
        allocated_resources: float,
        input_prompt: str,
        raw_output: str,
        extracted_score: Optional[float],
        model: str = "unknown",
        temperature: float = 0.0,
        duration: float = 0.0,
        success: bool = True,
        processed_data: Optional[Dict] = None
    ):
        """
        Log LLM call during evaluation phase
        
        Args:
            round_number: Round number
            agent: Agent information
            distribution_method: Distribution method
            allocated_resources: Amount of resources allocated
            input_prompt: Input prompt
            raw_output: LLM raw output
            extracted_score: Extracted score
            model: Model name
            temperature: Temperature parameter
            duration: Call duration
            success: Whether successful
            processed_data: Processed data (optional)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Update statistics
        self.total_calls += 1
        self.calls_by_round[round_number] = self.calls_by_round.get(round_number, 0) + 1
        
        # Write to CSV
        with open(self.csv_file, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                round_number,
                agent.get('id', 'Unknown'),
                agent.get('family_name', 'Unknown'),
                agent.get('value_type', 'Unknown'),
                agent.get('members', 0),
                agent.get('labor_force', 0),
                distribution_method,
                f"{allocated_resources:.2f}",
                'Evaluation',
                model,
                temperature,
                input_prompt,
                raw_output,
                extracted_score if extracted_score is not None else '',
                json.dumps(processed_data, ensure_ascii=False) if processed_data else '',
                f"{duration:.2f}",
                'Yes' if success else 'No'
            ])
    
    def log_negotiation_call(
        self,
        round_number: int,
        stage: str,
        agent: Optional[Dict[str, Any]],
        input_prompt: str,
        raw_output: str,
        model: str = "unknown",
        temperature: float = 0.0,
        duration: float = 0.0,
        success: bool = True,
        processed_data: Optional[Dict] = None
    ):
        """
        Log LLM call during negotiation phase
        
        Args:
            round_number: Round number
            stage: Negotiation stage (principles/principles-persuasion/framework/details/finalization)
            agent: Agent information (if single agent call)
            input_prompt: Input prompt
            raw_output: LLM raw output
            model: Model name
            temperature: Temperature parameter
            duration: Call duration
            success: Whether successful
            processed_data: Processed data (optional)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Update statistics
        self.total_calls += 1
        self.calls_by_round[round_number] = self.calls_by_round.get(round_number, 0) + 1
        
        # Negotiation stage descriptions
        stage_names = {
            'principles': 'Stage1-Determine Principles',
            'principles-persuasion': 'Stage1-Persuade Principles',
            'framework': 'Stage2-Negotiate Framework',
            'details': 'Stage3-Build Detailed Plan',
            'finalization': 'Stage4-Final Confirmation'
        }
        stage_display = stage_names.get(stage, f'Negotiation-{stage}')
        
        # Write to CSV
        with open(self.csv_file, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                round_number,
                agent.get('id', '') if agent else '',
                agent.get('family_name', '') if agent else 'All',
                agent.get('value_type', '') if agent else '',
                agent.get('members', '') if agent else '',
                agent.get('labor_force', '') if agent else '',
                stage_display,
                '',
                f'Negotiation/{stage}',
                model,
                temperature,
                input_prompt,
                raw_output,
                '',
                json.dumps(processed_data, ensure_ascii=False) if processed_data else '',
                f"{duration:.2f}",
                'Yes' if success else 'No'
            ])
    
    def print_statistics(self):
        """Print statistics"""
        print(f"\n📊 LLM Interaction Statistics:")
        print(f"   Total calls: {self.total_calls}")
        print(f"   Rounds involved: {len(self.calls_by_round)}")
        if self.calls_by_round:
            print(f"   Calls per round:")
            for round_num in sorted(self.calls_by_round.keys()):
                print(f"     Round {round_num}: {self.calls_by_round[round_num]} calls")
    
    def close(self):
        """Close logger"""
        self.print_statistics()
        print(f"✅ LLM interaction log saved to: {self.csv_file}")


# Global logger instance
_global_logger: Optional[LLMInteractionLogger] = None


def initialize_logger(log_dir: str = "llm_logs", experiment_id: str = None) -> LLMInteractionLogger:
    """Initialize global logger"""
    global _global_logger
    _global_logger = LLMInteractionLogger(log_dir, experiment_id)
    return _global_logger


def get_logger() -> Optional[LLMInteractionLogger]:
    """Get global logger"""
    return _global_logger


def close_logger():
    """Close global logger"""
    global _global_logger
    if _global_logger:
        _global_logger.close()
        _global_logger = None
