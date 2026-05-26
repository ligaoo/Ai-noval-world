from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.models.event import EventLog, PlotValue
from app.models.world import WorldConfig
from app.services.event_log_service import EventLogService
from app.services.narrative_service import NarrativeService


class AgentWriterContractTest(unittest.TestCase):
    def test_structured_agent_outputs_flow_into_writer_debug(self) -> None:
        project_root = Path(__file__).parent
        world = WorldConfig.from_directory(project_root / "worlds" / "dark_city_001")
        pov_id = world.chapter_goal.pov
        other_id = next(char.id for char in world.characters.characters if char.id != pov_id)

        with tempfile.TemporaryDirectory() as tmp_dir:
            sim_dir = Path(tmp_dir)
            event_service = EventLogService()
            event_service.append(
                sim_dir,
                EventLog(
                    event_id="evt_interaction_001",
                    event_level="plot",
                    time="day1_20:00",
                    location_id=world.map.locations[0].id,
                    actors=[pov_id],
                    event_type="interaction",
                    result="A locked door and a new scratch mark force the group to stop.",
                    visible_to=[pov_id],
                    plot_value=PlotValue(progress=1, mystery=2, conflict=2),
                    interaction_id="interaction_001",
                    source_interaction={
                        "agent_debug_metrics": {
                            "agent_reaction_count": 2,
                            "group_decision_count": 1,
                            "private_tendency_trigger_count": 1,
                            "relationship_update_count": 1,
                            "interaction_event_count": 5,
                        },
                        "agent_reactions": [
                            {
                                "reaction_id": "react_1",
                                "agent_id": pov_id,
                                "reaction_type": "question",
                                "target_agent": other_id,
                                "spoken_text": "Who touched the lock?",
                                "reasoning": "The fresh scratch mark looks recent.",
                                "will_express": True,
                            },
                            {
                                "reaction_id": "react_2",
                                "agent_id": other_id,
                                "reaction_type": "withhold",
                                "target_agent": pov_id,
                                "spoken_text": "",
                                "reasoning": "Protect a private secret.",
                                "will_express": False,
                            },
                        ],
                        "group_decision": {
                            "decision_id": "decision_1",
                            "participants": [pov_id, other_id],
                            "topic": "open the locked door",
                            "decision_type": "majority",
                        },
                        "private_tendency_triggers": [
                            {
                                "trigger_id": "trigger_1",
                                "agent_id": other_id,
                                "trigger_type": "secret_protection",
                                "resulting_bias": "avoid sharing what they know about the lock",
                            }
                        ],
                        "relationship_updates": [
                            {
                                "impact_id": "impact_1",
                                "source_agent": pov_id,
                                "target_agent": other_id,
                                "impact_type": "suspicion_rise",
                                "delta_value": 1,
                                "cause": "The refusal to explain the lock increased suspicion.",
                            }
                        ],
                        "interaction_events": [
                            {
                                "event_id": "ie_1",
                                "event_type": "agent_reaction",
                                "summary": "The protagonist questioned who touched the lock.",
                            },
                            {
                                "event_id": "ie_2",
                                "event_type": "group_decision",
                                "summary": "The group argued before deciding whether to open the door.",
                            },
                            {
                                "event_id": "ie_3",
                                "event_type": "private_tendency_trigger",
                                "summary": "A private secret made one witness avoid the truth.",
                            },
                            {
                                "event_id": "ie_4",
                                "event_type": "relationship_update",
                                "summary": "Suspicion rose after the refusal to explain.",
                            },
                            {
                                "event_id": "ie_5",
                                "event_type": "relationship_update",
                                "summary": "The argument left a visible crack in the group.",
                            },
                        ],
                    },
                ),
            )

            service = NarrativeService(
                world=world,
                sim_dir=sim_dir,
                llm_client=None,
                force_rule_based=True,
                enable_consistency_check=False,
            )
            result = service.generate_chapter()

            debug_data = json.loads((sim_dir / "chapter_debug.json").read_text(encoding="utf-8"))
            self.assertEqual(debug_data["counts"]["agent_reaction_count"], 2)
            self.assertEqual(debug_data["counts"]["group_decision_count"], 1)
            self.assertEqual(debug_data["counts"]["private_tendency_trigger_count"], 1)
            self.assertEqual(debug_data["counts"]["relationship_update_count"], 1)
            self.assertEqual(debug_data["counts"]["interaction_event_count"], 5)
            self.assertTrue(debug_data["writer_input_contract_enforced"])
            self.assertTrue(debug_data["traceability"])

            chapter_plan = json.loads((sim_dir / "chapter_plan.json").read_text(encoding="utf-8"))
            self.assertIn("writer_structured_context", chapter_plan)
            self.assertEqual(
                chapter_plan["writer_structured_context"]["counts"]["interaction_event_count"],
                5,
            )

            draft = result["draft"]
            self.assertIn("expressed question", draft)
            self.assertIn("group made a majority decision", draft)
            self.assertIn("suspicion_rise", draft)


if __name__ == "__main__":
    unittest.main()
