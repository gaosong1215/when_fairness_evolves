"""
Negotiation Discussion Recording System
Used to save and analyze all discussion content, decision processes, and results during negotiation
"""
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from fairness_sim.llm_client import get_model_name

@dataclass
class DiscussionTurn:
    """Record of a single discussion turn"""
    turn_id: str                    # Turn ID
    speaker_id: int                 # Speaker ID  
    speaker_name: str               # Speaker family name
    speaker_value_type: str         # Speaker's value type
    stage: str                      # Negotiation stage
    round_number: int               # Round number
    timestamp: str                  # Timestamp
    content: str                    # Speech content
    speech_type: str                # Speech type: proposal/response/objection/agreement/compromise
    target_topic: str               # Discussion topic
    references: List[str]           # Referenced turn IDs
    proposal_changes: Optional[Dict] # Proposal changes (if any)
    sentiment: str                  # Sentiment: positive/neutral/negative
    keywords: List[str]             # Extracted keywords

@dataclass 
class StageRecord:
    """Stage record"""
    stage_name: str                 # Stage name
    start_time: str                 # Start time
    end_time: str                   # End time
    duration: float                 # Duration (seconds)
    participants: List[int]         # Participant ID list
    discussion_turns: List[DiscussionTurn]  # Discussion turns
    decisions_made: List[Dict]      # Decisions reached
    consensus_level: float          # Consensus level (0-1)
    conflicts: List[Dict]           # Conflict records
    stage_outcome: str              # Stage outcome

@dataclass
class NegotiationSession:
    """Complete negotiation session record"""
    session_id: str                 # Session ID
    round_number: int               # Round number
    start_time: str                 # Start time
    end_time: str                   # End time
    total_duration: float           # Total duration
    participants: List[Dict]        # Participant information
    total_resources: Dict[str, float]  # Total resources
    survival_needs: Dict[int, Dict[str, float]]  # Survival needs
    
    # Negotiation process
    stages: List[StageRecord]       # Stage records
    final_allocation: Dict[int, Dict[str, float]]  # Final allocation
    success: bool                   # Whether successful
    failure_reason: Optional[str]   # Failure reason
    
    # Statistics
    total_turns: int                # Total number of turns
    consensus_reached: bool         # Whether consensus reached
    average_satisfaction: float     # Average satisfaction
    
    # Metadata
    metadata: Dict[str, Any]        # Other metadata


class NegotiationLogger:
    """Negotiation process recorder"""
    
    def __init__(self, session_id: str, output_dir: str = "negotiation_logs"):
        """Initialize recorder
        
        Args:
            session_id: Session ID
            output_dir: Output directory
        """
        self.session_id = session_id
        # Root directory
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Independent subdirectory for this session
        self.session_dir = self.output_dir / f"session_{session_id}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Current session record
        self.current_session: Optional[NegotiationSession] = None
        self.current_stage: Optional[StageRecord] = None
        self.turn_counter = 0
        
        # Live log file (placed in session directory)
        self.log_file = self.session_dir / "live.jsonl"
        
    def start_session(self, round_number: int, participants: List[Dict], 
                     total_resources: Dict[str, float], 
                     survival_needs: Dict[int, Dict[str, float]]):
        """Start a new negotiation session"""
        self.current_session = NegotiationSession(
            session_id=self.session_id,
            round_number=round_number,
            start_time=datetime.now().isoformat(),
            end_time="",
            total_duration=0.0,
            participants=participants,
            total_resources=total_resources,
            survival_needs=survival_needs,
            stages=[],
            final_allocation={},
            success=False,
            failure_reason=None,
            total_turns=0,
            consensus_reached=False,
            average_satisfaction=0.0,
            metadata={}
        )
        
        # Record session start
        self._write_live_log("session_start", {
            "session_id": self.session_id,
            "timestamp": self.current_session.start_time,
            "participants": participants,
            "total_resources": total_resources
        })
        
        print(f"📝 Recording negotiation session: {self.session_id}")
    
    def start_stage(self, stage_name: str, participants: List[int]):
        """Start a new negotiation stage"""
        if self.current_stage:
            self.end_stage()
        
        self.current_stage = StageRecord(
            stage_name=stage_name,
            start_time=datetime.now().isoformat(),
            end_time="",
            duration=0.0,
            participants=participants,
            discussion_turns=[],
            decisions_made=[],
            consensus_level=0.0,
            conflicts=[],
            stage_outcome=""
        )
        
        # Record stage start
        self._write_live_log("stage_start", {
            "stage_name": stage_name,
            "timestamp": self.current_stage.start_time,
            "participants": participants
        })
        
        print(f"  📋 Starting stage: {stage_name}")
    
    def log_discussion_turn(self, speaker_id: int, speaker_name: str, 
                           speaker_value_type: str, content: str,
                           speech_type: str = "statement",
                           target_topic: str = "",
                           references: List[str] = None,
                           proposal_changes: Dict = None):
        """Record a discussion turn"""
        if not self.current_stage:
            raise ValueError("Must start a stage before recording turns")
        
        self.turn_counter += 1
        turn_id = f"turn_{self.session_id}_{self.turn_counter:04d}"
        
        turn = DiscussionTurn(
            turn_id=turn_id,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            speaker_value_type=speaker_value_type,
            stage=self.current_stage.stage_name,
            round_number=self.current_session.round_number,
            timestamp=datetime.now().isoformat(),
            content=content,
            speech_type=speech_type,
            target_topic=target_topic,
            references=references or [],
            proposal_changes=proposal_changes,
            sentiment=self._analyze_sentiment(content),
            keywords=self._extract_keywords(content)
        )
        
        self.current_stage.discussion_turns.append(turn)
        
        # Live recording
        self._write_live_log("discussion_turn", asdict(turn))
        
        print(f"    💬 Recording turn: {speaker_name} family ({speech_type})")
        return turn_id
    
    def log_decision(self, decision_type: str, decision_content: Dict, 
                    supporters: List[int], opponents: List[int]):
        """Record decision result"""
        if not self.current_stage:
            return
        
        decision = {
            "timestamp": datetime.now().isoformat(),
            "type": decision_type,
            "content": decision_content,
            "supporters": supporters,
            "opponents": opponents,
            "consensus_level": len(supporters) / (len(supporters) + len(opponents)) if (len(supporters) + len(opponents)) > 0 else 0
        }
        
        self.current_stage.decisions_made.append(decision)
        
        # Live recording
        self._write_live_log("decision", decision)
        
        print(f"    ⚖️ Recording decision: {decision_type}")
    
    def log_negotiation_call(self, agent_id: int, stage: str, prompt_content: str, 
                           response_content: str, target_topic: str):
        """Record LLM call during negotiation process
        
        Args:
            agent_id: Agent ID
            stage: Negotiation stage
            prompt_content: Prompt content
            response_content: Response content
            target_topic: Target topic
        """
        if not self.current_stage:
            return
        
        # Find corresponding agent information
        agent_name = f"Agent_{agent_id}"
        agent_value_type = "unknown"
        
        # Try to get agent information from current session
        if self.current_session and hasattr(self.current_session, 'participants'):
            for participant in self.current_session.participants:
                if participant.get('id') == agent_id:
                    agent_name = participant.get('family_name', f"Agent_{agent_id}")
                    agent_value_type = participant.get('value_type', 'unknown')
                    break
        
        # Create discussion turn record
        turn_id = f"{stage}_{agent_id}_{int(time.time())}"
        
        discussion_turn = DiscussionTurn(
            turn_id=turn_id,
            speaker_id=agent_id,
            speaker_name=agent_name,
            speaker_value_type=agent_value_type,
            stage=stage,
            round_number=self.current_session.round_number if self.current_session else 1,
            timestamp=datetime.now().isoformat(),
            content=response_content,
            speech_type="llm_response",
            target_topic=target_topic,
            references=[],
            proposal_changes=None,
            sentiment=self._analyze_sentiment(response_content),
            keywords=self._extract_keywords(response_content)
        )
        
        self.current_stage.discussion_turns.append(discussion_turn)
        
        # Also record to LLM interaction log (if available)
        try:
            from fairness_sim.logging.llm_interaction import get_logger
            llm_logger = get_logger()
            if llm_logger:
                llm_logger.log_evaluation_call(
                    round_number=self.current_session.round_number if self.current_session else 1,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    agent_value_type=agent_value_type,
                    prompt=prompt_content,
                    raw_output=response_content,
                    extracted_score=None,
                    model=get_model_name(),
                    temperature=0.7,
                    duration=0.0,
                    success=True
                )
        except Exception:
            # If LLM log recording fails, don't affect negotiation log
            pass
    
    def log_conflict(self, conflict_topic: str, conflicting_parties: List[int], 
                    conflict_description: str, resolution_status: str = "unresolved"):
        """Record conflict"""
        if not self.current_stage:
            return
        
        conflict = {
            "timestamp": datetime.now().isoformat(),
            "topic": conflict_topic,
            "parties": conflicting_parties,
            "description": conflict_description,
            "status": resolution_status
        }
        
        self.current_stage.conflicts.append(conflict)
        
        # Live recording
        self._write_live_log("conflict", conflict)
        
        print(f"    ⚠️ Recording conflict: {conflict_topic}")
    
    def end_stage(self, stage_outcome: str = "", consensus_level: float = 0.0):
        """End current stage"""
        if not self.current_stage:
            return
        
        self.current_stage.end_time = datetime.now().isoformat()
        self.current_stage.duration = self._calculate_duration(
            self.current_stage.start_time, 
            self.current_stage.end_time
        )
        self.current_stage.stage_outcome = stage_outcome
        self.current_stage.consensus_level = consensus_level
        
        # Add to session record
        self.current_session.stages.append(self.current_stage)
        
        # Live recording
        self._write_live_log("stage_end", {
            "stage_name": self.current_stage.stage_name,
            "duration": self.current_stage.duration,
            "outcome": stage_outcome,
            "consensus_level": consensus_level,
            "turns_count": len(self.current_stage.discussion_turns),
            "decisions_count": len(self.current_stage.decisions_made),
            "conflicts_count": len(self.current_stage.conflicts)
        })
        
        print(f"  ✅ Stage ended: {self.current_stage.stage_name} (duration: {self.current_stage.duration:.1f}s)")
        self.current_stage = None
    
    def end_session(self, final_allocation: Dict[int, Dict[str, float]], 
                   success: bool, failure_reason: str = None,
                   average_satisfaction: float = 0.0):
        """End negotiation session"""
        if not self.current_session:
            return
        
        # End current stage (if any)
        if self.current_stage:
            self.end_stage()
        
        self.current_session.end_time = datetime.now().isoformat()
        self.current_session.total_duration = self._calculate_duration(
            self.current_session.start_time,
            self.current_session.end_time
        )
        self.current_session.final_allocation = final_allocation
        self.current_session.success = success
        self.current_session.failure_reason = failure_reason
        self.current_session.total_turns = self.turn_counter
        self.current_session.average_satisfaction = average_satisfaction
        
        # Calculate overall statistics
        self.current_session.consensus_reached = any(
            stage.consensus_level > 0.8 for stage in self.current_session.stages
        )
        
        # Save complete record
        self._save_complete_session()
        
        # Live recording of session end
        self._write_live_log("session_end", {
            "success": success,
            "total_duration": self.current_session.total_duration,
            "total_turns": self.turn_counter,
            "consensus_reached": self.current_session.consensus_reached
        })
        
        print(f"📝 Negotiation session recording complete: {self.session_id}")
        print(f"   Total duration: {self.current_session.total_duration:.1f}s")
        print(f"   Total turns: {self.turn_counter}")
        print(f"   Success: {success}")
    
    def _write_live_log(self, event_type: str, data: Dict):
        """Write live log"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "session_id": self.session_id,
            "data": data
        }
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def _save_complete_session(self):
        """Save complete session record"""
        # JSON format (placed in session directory)
        json_file = self.session_dir / "complete.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.current_session), f, ensure_ascii=False, indent=2)
        
        # Generate readable text summary (placed in session directory)
        summary_file = self.session_dir / "summary.txt"
        self._generate_text_summary(summary_file)
        
        print(f"   📄 Complete record saved: {json_file}")
        print(f"   📄 Summary saved: {summary_file}")
    
    def _generate_text_summary(self, summary_file: Path):
        """Generate readable text summary"""
        with open(summary_file, 'w', encoding='utf-8') as f:
            session = self.current_session
            
            f.write(f"Negotiation Session Summary Report\n")
            f.write(f"{'='*50}\n\n")
            
            f.write(f"Session ID: {session.session_id}\n")
            f.write(f"Round Number: {session.round_number}\n")
            f.write(f"Start Time: {session.start_time}\n")
            f.write(f"End Time: {session.end_time}\n")
            f.write(f"Total Duration: {session.total_duration:.1f}s\n")
            f.write(f"Success: {session.success}\n")
            f.write(f"Consensus Reached: {session.consensus_reached}\n\n")
            
            f.write(f"Participants:\n")
            for participant in session.participants:
                f.write(f"  - {participant['family_name']} family ({participant['value_type']})\n")
            f.write(f"\n")
            
            f.write(f"Total Resources: {session.total_resources}\n\n")
            
            # Stage summaries
            f.write(f"Negotiation Stage Summaries:\n")
            f.write(f"-" * 30 + "\n")
            
            for i, stage in enumerate(session.stages, 1):
                f.write(f"\nStage {i}: {stage.stage_name}\n")
                f.write(f"  Duration: {stage.duration:.1f}s\n")
                f.write(f"  Turn Count: {len(stage.discussion_turns)}\n")
                f.write(f"  Decisions Made: {len(stage.decisions_made)}\n")
                f.write(f"  Conflicts: {len(stage.conflicts)}\n")
                f.write(f"  Consensus Level: {stage.consensus_level:.2f}\n")
                f.write(f"  Outcome: {stage.stage_outcome}\n")
                
                # Main discussion summary
                if stage.discussion_turns:
                    f.write(f"  Main Discussion:\n")
                    for turn in stage.discussion_turns[:3]:  # Show only first 3 turns
                        f.write(f"    {turn.speaker_name}: {turn.content[:100]}...\n")
            
            # Final allocation
            f.write(f"\nFinal Allocation Results:\n")
            f.write(f"-" * 30 + "\n")
            for agent_id, allocation in session.final_allocation.items():
                agent_name = next(p['family_name'] for p in session.participants if p['id'] == agent_id)
                total = sum(allocation.values())
                f.write(f"  {agent_name} family: {total:.2f}\n")
    
    def _analyze_sentiment(self, content: str) -> str:
        """Simple sentiment analysis"""
        positive_words = ["agree", "support", "approve", "good", "satisfied", "fair", "reasonable", 
                         "excellent", "acceptable", "positive", "happy", "pleased"]
        negative_words = ["oppose", "disagree", "dissatisfied", "unfair", "unreasonable", "problem", 
                         "worried", "concern", "bad", "unacceptable", "negative", "unhappy"]
        
        content_lower = content.lower()
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords"""
        keywords = []
        
        # Simple keyword extraction
        key_terms = [
            "allocation", "resource", "fair", "need", "contribution", "labor", "family", "member",
            "survival", "basic", "equal", "based on need", "based on work", "negotiation", 
            "compromise", "agree", "distribution", "equity", "merit", "demand"
        ]
        
        content_lower = content.lower()
        for term in key_terms:
            if term in content_lower:
                keywords.append(term)
        
        return keywords
    
    def _calculate_duration(self, start_time: str, end_time: str) -> float:
        """Calculate duration (seconds)"""
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
        return (end - start).total_seconds()


class NegotiationAnalyzer:
    """Negotiation record analyzer"""
    
    def __init__(self, log_directory: str = "negotiation_logs"):
        self.log_dir = Path(log_directory)
    
    def analyze_session(self, session_id: str) -> Dict[str, Any]:
        """Analyze a single session"""
        # Support new directory structure: session_{id}/complete.json
        json_file = self.log_dir / f"session_{session_id}" / "complete.json"
        
        if not json_file.exists():
            # Support legacy flat naming
            legacy = self.log_dir / f"session_{session_id}_complete.json"
            if legacy.exists():
                json_file = legacy
            else:
                raise FileNotFoundError(f"Session record file not found: {json_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        return self._generate_analysis(session_data)
    
    def _generate_analysis(self, session_data: Dict) -> Dict[str, Any]:
        """Generate analysis report"""
        analysis = {
            "basic_stats": self._analyze_basic_stats(session_data),
            "communication_patterns": self._analyze_communication(session_data),
            "consensus_evolution": self._analyze_consensus(session_data),
            "value_conflicts": self._analyze_value_conflicts(session_data),
            "efficiency_metrics": self._analyze_efficiency(session_data)
        }
        
        return analysis
    
    def _analyze_basic_stats(self, session_data: Dict) -> Dict:
        """Basic statistics analysis"""
        return {
            "total_duration": session_data["total_duration"],
            "total_turns": session_data["total_turns"],
            "stages_count": len(session_data["stages"]),
            "success_rate": 1 if session_data["success"] else 0,
            "consensus_reached": session_data["consensus_reached"]
        }
    
    def _analyze_communication(self, session_data: Dict) -> Dict:
        """Communication pattern analysis"""
        all_turns = []
        for stage in session_data["stages"]:
            all_turns.extend(stage["discussion_turns"])
        
        # Group turn counts by value type
        value_type_counts = {}
        for turn in all_turns:
            vt = turn["speaker_value_type"]
            value_type_counts[vt] = value_type_counts.get(vt, 0) + 1
        
        # Speech type distribution
        speech_type_counts = {}
        for turn in all_turns:
            st = turn["speech_type"]
            speech_type_counts[st] = speech_type_counts.get(st, 0) + 1
        
        return {
            "turns_by_value_type": value_type_counts,
            "speech_type_distribution": speech_type_counts,
            "average_turn_length": sum(len(turn["content"]) for turn in all_turns) / len(all_turns) if all_turns else 0
        }
    
    def _analyze_consensus(self, session_data: Dict) -> Dict:
        """Consensus evolution analysis"""
        consensus_evolution = []
        
        for stage in session_data["stages"]:
            consensus_evolution.append({
                "stage": stage["stage_name"],
                "consensus_level": stage["consensus_level"],
                "decisions_made": len(stage["decisions_made"]),
                "conflicts": len(stage["conflicts"])
            })
        
        return {
            "evolution": consensus_evolution,
            "final_consensus": session_data["consensus_reached"],
            "peak_consensus": max((stage["consensus_level"] for stage in session_data["stages"]), default=0)
        }
    
    def _analyze_value_conflicts(self, session_data: Dict) -> Dict:
        """Value conflict analysis"""
        conflicts_by_stage = {}
        
        for stage in session_data["stages"]:
            stage_conflicts = []
            for conflict in stage["conflicts"]:
                # Analyze value types involved in conflict
                participants = session_data["participants"]
                conflict_values = []
                for party_id in conflict["parties"]:
                    participant = next(p for p in participants if p["id"] == party_id)
                    conflict_values.append(participant["value_type"])
                
                stage_conflicts.append({
                    "topic": conflict["topic"],
                    "involved_values": conflict_values,
                    "status": conflict["status"]
                })
            
            conflicts_by_stage[stage["stage_name"]] = stage_conflicts
        
        return conflicts_by_stage
    
    def _analyze_efficiency(self, session_data: Dict) -> Dict:
        """Efficiency metrics analysis"""
        total_time = session_data["total_duration"]
        total_turns = session_data["total_turns"]
        
        return {
            "time_per_turn": total_time / total_turns if total_turns > 0 else 0,
            "time_per_stage": total_time / len(session_data["stages"]) if session_data["stages"] else 0,
            "decisions_per_minute": len([d for stage in session_data["stages"] for d in stage["decisions_made"]]) / (total_time / 60) if total_time > 0 else 0,
            "success_rate": 1 if session_data["success"] else 0
        }
