from __future__ import annotations

import uuid
from typing import List, Optional

from app.models.interaction import (
    AgentReaction,
    InteractionProposal,
    InteractionResult,
)
from app.models.state import WorldState
from app.models.world import CharacterProfile, WorldConfig


class AgentReactionCheck:
    """
    关键事件发生后，各 Agent 根据自己的目标、性格、秘密、恐惧、信任关系生成反应意图。
    不绑定任何固定剧情逻辑。
    """

    def __init__(self, world: WorldConfig):
        self.world = world

    def generate_reactions_for_interaction(
        self,
        proposal: InteractionProposal,
        state: WorldState,
        primary_trigger: str,
    ) -> List[AgentReaction]:
        """
        为交互中的每个参与者生成 Agent 驱动的反应。
        """
        reactions: List[AgentReaction] = []
        all_agents = set(proposal.participants + proposal.observers)

        for agent_id in all_agents:
            profile = self._get_agent_profile(agent_id)
            if not profile:
                continue

            runtime = state.characters.get(agent_id)
            if not runtime:
                continue

            agent_reactions = self._generate_agent_reactions(
                agent_id,
                profile,
                runtime,
                proposal,
                primary_trigger,
                state,
            )
            reactions.extend(agent_reactions)

        return reactions

    def _generate_agent_reactions(
        self,
        agent_id: str,
        profile: CharacterProfile,
        runtime,
        proposal: InteractionProposal,
        trigger: str,
        state: WorldState,
    ) -> List[AgentReaction]:
        """
        为单个 Agent 生成反应列表。
        """
        reactions: List[AgentReaction] = []

        if trigger == "clue_discovered":
            reactions.extend(self._clue_discovered_reactions(agent_id, profile, runtime, proposal, state))
        elif trigger == "proposal_made":
            reactions.extend(self._proposal_reactions(agent_id, profile, runtime, proposal, state))
        elif trigger == "accusation_made":
            reactions.extend(self._accusation_reactions(agent_id, profile, runtime, proposal, state))
        elif trigger == "information_revealed":
            reactions.extend(self._information_revealed_reactions(agent_id, profile, runtime, proposal, state))
        else:
            reactions.extend(self._general_conflict_reactions(agent_id, profile, runtime, proposal, state))

        return reactions

    def _clue_discovered_reactions(
        self,
        agent_id: str,
        profile: CharacterProfile,
        runtime,
        proposal: InteractionProposal,
        state: WorldState,
    ) -> List[AgentReaction]:
        reactions = []
        speaker = proposal.intents[0].agent_id if proposal.intents else None

        relations = runtime.relationships
        to_speaker = relations.get(speaker, None) if speaker and speaker != agent_id else None

        personality_traits = self._get_personality_traits(profile)
        has_secret = len(profile.secrets) > 0

        reaction_types = []

        if has_secret:
            for idx, secret in enumerate(profile.secrets):
                if self._secret_is_threatened(secret, proposal.topic or "", state):
                    reaction_types.append({
                        "type": "withhold",
                        "urgency": 3,
                        "confidence": 0.9,
                        "reason": "This information threatens a personal secret",
                        "private_motivation": f"Protecting secret #{idx}",
                    })

        if to_speaker and to_speaker.suspicion > to_speaker.trust:
            reaction_types.append({
                "type": "doubt",
                "target": speaker,
                "urgency": 2,
                "confidence": 0.6 + (to_speaker.suspicion / 20),
                "reason": "Low trust in the person making the discovery",
            })

        if "curious" in personality_traits or "analytical" in personality_traits:
            reaction_types.append({
                "type": "question",
                "target": speaker,
                "urgency": 1,
                "confidence": 0.7,
                "reason": "Curiosity about the discovery",
            })

        if len(runtime.known_facts) >= 3 and "cautious" not in personality_traits:
            reaction_types.append({
                "type": "request_share",
                "target": speaker,
                "urgency": 1,
                "confidence": 0.6,
                "reason": "Believes in sharing information openly",
            })

        if not reaction_types:
            reaction_types.append({
                "type": "silent_record",
                "urgency": 0,
                "confidence": 0.8,
                "reason": "Observing silently",
                "will_express": False,
            })

        for rt in reaction_types:
            reaction = AgentReaction(
                reaction_id=f"react_{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                reaction_type=rt["type"],
                trigger_event_type="clue_discovered",
                target_agent=rt.get("target"),
                target_fact=proposal.topic,
                urgency=rt.get("urgency", 1),
                confidence=rt.get("confidence", 0.5),
                reasoning=rt.get("reason", ""),
                private_motivation=rt.get("private_motivation", ""),
                will_express=rt.get("will_express", True),
                spoken_text=self._generate_spoken_text(rt["type"], agent_id, rt.get("target")),
                pressure_delta=rt.get("urgency", 1),
                trigger_source="agent_mind",
            )
            reactions.append(reaction)

        return reactions

    def _proposal_reactions(
        self,
        agent_id: str,
        profile: CharacterProfile,
        runtime,
        proposal: InteractionProposal,
        state: WorldState,
    ) -> List[AgentReaction]:
        reactions = []
        proposer = proposal.intents[0].agent_id if proposal.intents else None

        if proposer == agent_id:
            return reactions

        relations = runtime.relationships
        to_proposer = relations.get(proposer, None) if proposer else None

        personality_traits = self._get_personality_traits(profile)

        if to_proposer:
            if to_proposer.trust > 5:
                reactions.append(AgentReaction(
                    reaction_id=f"react_{uuid.uuid4().hex[:8]}",
                    agent_id=agent_id,
                    reaction_type="support",
                    trigger_event_type="proposal_made",
                    target_agent=proposer,
                    urgency=1,
                    confidence=0.7,
                    reasoning="Trusts the proposer",
                    will_express=True,
                    spoken_text=f"I agree with {proposer}'s suggestion.",
                    pressure_delta=0,
                ))
            elif to_proposer.suspicion > 5:
                reactions.append(AgentReaction(
                    reaction_id=f"react_{uuid.uuid4().hex[:8]}",
                    agent_id=agent_id,
                    reaction_type="doubt",
                    trigger_event_type="proposal_made",
                    target_agent=proposer,
                    urgency=2,
                    confidence=0.6,
                    reasoning="Suspicious of the proposer's motives",
                    will_express=True,
                    spoken_text="I'm not sure that's the right move.",
                    pressure_delta=1,
                ))

        if "skeptical" in personality_traits:
            reactions.append(AgentReaction(
                reaction_id=f"react_{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                reaction_type="demand_verification",
                trigger_event_type="proposal_made",
                target_agent=proposer,
                urgency=2,
                confidence=0.7,
                reasoning="Needs verification before committing",
                will_express=True,
                spoken_text="What evidence do we have for this?",
                pressure_delta=1,
            ))

        if "independent" in personality_traits and len(reactions) == 0:
            reactions.append(AgentReaction(
                reaction_id=f"react_{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                reaction_type="suggest_alternative",
                trigger_event_type="proposal_made",
                target_agent=proposer,
                urgency=1,
                confidence=0.6,
                reasoning="Prefers to explore options",
                will_express=True,
                spoken_text="Perhaps we could consider another approach.",
                pressure_delta=0,
            ))

        if not reactions:
            reactions.append(AgentReaction(
                reaction_id=f"react_{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                reaction_type="observe",
                trigger_event_type="proposal_made",
                urgency=0,
                confidence=0.9,
                reasoning="Observing group dynamics",
                will_express=False,
                pressure_delta=0,
            ))

        return reactions

    def _accusation_reactions(
        self,
        agent_id: str,
        profile: CharacterProfile,
        runtime,
        proposal: InteractionProposal,
        state: WorldState,
    ) -> List[AgentReaction]:
        reactions = []
        accuser = proposal.intents[0].agent_id if proposal.intents else None
        accused = None

        for intent in proposal.intents:
            if intent.target_agents:
                accused = intent.target_agents[0]
                break

        if accuser == agent_id:
            return reactions

        relations = runtime.relationships
        to_accuser = relations.get(accuser, None) if accuser else None
        to_accused = relations.get(accused, None) if accused else None

        if accused == agent_id:
            reactions.append(AgentReaction(
                reaction_id=f"react_{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                reaction_type="deny",
                trigger_event_type="accusation_made",
                target_agent=accuser,
                urgency=4,
                confidence=0.95,
                reasoning="Was directly accused",
                will_express=True,
                spoken_text="That's not true! I had nothing to do with it.",
                pressure_delta=3,
            ))

            if len(profile.secrets) > 0:
                reactions.append(AgentReaction(
                    reaction_id=f"react_{uuid.uuid4().hex[:8]}",
                    agent_id=agent_id,
                    reaction_type="deflect",
                    trigger_event_type="accusation_made",
                    target_agent=accuser,
                    urgency=3,
                    confidence=0.6,
                    reasoning="Deflecting attention from self",
                    private_motivation="Protecting personal secrets",
                    will_express=True,
                    spoken_text="What about you? Where were you?",
                    pressure_delta=2,
                ))

        elif to_accused and to_accused.trust > 3:
            reactions.append(AgentReaction(
                reaction_id=f"react_{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                reaction_type="protect",
                trigger_event_type="accusation_made",
                target_agent=accused,
                urgency=2,
                confidence=0.7,
                reasoning="Trusts and defends the accused",
                will_express=True,
                spoken_text=f"I don't believe {accused} could have done this.",
                pressure_delta=2,
            ))

        if to_accuser and to_accuser.hostility > 3:
            reactions.append(AgentReaction(
                reaction_id=f"react_{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                reaction_type="challenge",
                trigger_event_type="accusation_made",
                target_agent=accuser,
                urgency=3,
                confidence=0.7,
                reasoning="Hostile relationship with accuser",
                will_express=True,
                spoken_text="You're always looking for someone to blame.",
                pressure_delta=2,
            ))

        if not reactions:
            reactions.append(AgentReaction(
                reaction_id=f"react_{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                reaction_type="observe",
                trigger_event_type="accusation_made",
                urgency=1,
                confidence=0.8,
                reasoning="Watching the accusation unfold",
                will_express=False,
                pressure_delta=1,
            ))

        return reactions

    def _information_revealed_reactions(
        self,
        agent_id: str,
        profile: CharacterProfile,
        runtime,
        proposal: InteractionProposal,
        state: WorldState,
    ) -> List[AgentReaction]:
        reactions = []
        speaker = proposal.intents[0].agent_id if proposal.intents else None

        if speaker == agent_id:
            return reactions

        for idx, secret in enumerate(profile.secrets):
            if secret in (proposal.topic or "") or self._facts_imply_secret(proposal.intents, secret):
                reactions.append(AgentReaction(
                    reaction_id=f"react_{uuid.uuid4().hex[:8]}",
                    agent_id=agent_id,
                    reaction_type="withhold",
                    trigger_event_type="information_revealed",
                    urgency=4,
                    confidence=0.9,
                    reasoning="Information threatens personal secret",
                    private_motivation=f"Protecting secret #{idx}",
                    will_express=False,
                    pressure_delta=2,
                    trigger_source="private_tendency",
                ))
                break

        relations = runtime.relationships
        to_speaker = relations.get(speaker, None) if speaker else None

        if to_speaker and to_speaker.trust < -2:
            reactions.append(AgentReaction(
                reaction_id=f"react_{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                reaction_type="doubt",
                trigger_event_type="information_revealed",
                target_agent=speaker,
                urgency=2,
                confidence=0.6 + abs(to_speaker.trust) / 10,
                reasoning="Doesn't trust the speaker",
                will_express=True,
                spoken_text="I'm not sure I believe that.",
                pressure_delta=1,
            ))

        if not reactions:
            reactions.append(AgentReaction(
                reaction_id=f"react_{uuid.uuid4().hex[:8]}",
                agent_id=agent_id,
                reaction_type="silent_record",
                trigger_event_type="information_revealed",
                urgency=0,
                confidence=0.8,
                reasoning="Recording information internally",
                will_express=False,
                pressure_delta=0,
            ))

        return reactions

    def _general_conflict_reactions(
        self,
        agent_id: str,
        profile: CharacterProfile,
        runtime,
        proposal: InteractionProposal,
        state: WorldState,
    ) -> List[AgentReaction]:
        reactions = []

        reactions.append(AgentReaction(
            reaction_id=f"react_{uuid.uuid4().hex[:8]}",
            agent_id=agent_id,
            reaction_type="observe",
            trigger_event_type="conflict_observed",
            urgency=1,
            confidence=0.7,
            reasoning="Observing the situation",
            will_express=False,
            pressure_delta=0,
        ))

        return reactions

    def _get_agent_profile(self, agent_id: str) -> Optional[CharacterProfile]:
        for char in self.world.characters.characters:
            if char.id == agent_id:
                return char
        return None

    @staticmethod
    def _get_personality_traits(profile: CharacterProfile) -> List[str]:
        if isinstance(profile.personality, dict):
            traits = profile.personality.get("traits", [])
            if isinstance(traits, list):
                return [str(t).lower() for t in traits]
        return []

    @staticmethod
    def _secret_is_threatened(secret: str, topic: str, state: WorldState) -> bool:
        if not topic:
            return False
        secret_keywords = set(secret.lower().split())
        topic_keywords = set(topic.lower().split())
        return len(secret_keywords & topic_keywords) >= 1

    @staticmethod
    def _facts_imply_secret(intents, secret: str) -> bool:
        secret_words = set(secret.lower().split())
        for intent in intents:
            for fact in intent.will_say:
                fact_words = set(fact.lower().split())
                if len(secret_words & fact_words) >= 2:
                    return True
        return False

    @staticmethod
    def _generate_spoken_text(reaction_type: str, agent_id: str, target: Optional[str] = None) -> str:
        texts = {
            "question": "Wait, let me ask something about that.",
            "challenge": "Hold on, that doesn't add up.",
            "observe": "",
            "request_share": "Can you tell us more?",
            "withhold": "",
            "silent_record": "",
            "action_proposal": "I think we should...",
            "deny": "That's not right.",
            "deflect": "What about the other possibilities?",
            "support": "I think that makes sense.",
            "accuse": "There's something off here.",
            "protect": f"Wait, let's not jump to conclusions about {target or 'them'}.",
            "doubt": "I'm not convinced.",
            "agree": "That seems right to me.",
            "disagree": "I don't think so.",
            "suggest_alternative": "What if we tried something else?",
            "demand_verification": "Can we verify this?",
        }
        return texts.get(reaction_type, "")
