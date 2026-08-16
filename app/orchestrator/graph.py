import logging
from typing import Dict, Any, Callable, Union
from app.orchestrator.state import ConversationState
from app.orchestrator.nodes import (
    intake, symptom_collector, safety_check, retrieve, deep_reasoning, generate, triage_router,
)

logger = logging.getLogger(__name__)
END = "END"

class StateGraph:
    """A lightweight, zero-dependency implementation of a State Machine Graph matching LangGraph's API."""
    def __init__(self, state_schema: type):
        self.state_schema = state_schema
        self.nodes: Dict[str, Callable] = {}
        self.edges: Dict[str, str] = {}
        self.conditional_edges: Dict[str, tuple[Callable, Dict[str, str]]] = {}
        self.entry_point: Union[str, None] = None

    def add_node(self, name: str, func: Callable) -> None:
        self.nodes[name] = func

    def add_edge(self, from_node: str, to_node: str) -> None:
        self.edges[from_node] = to_node

    def add_conditional_edges(self, from_node: str, routing_func: Callable, mapping: Dict[str, str]) -> None:
        self.conditional_edges[from_node] = (routing_func, mapping)

    def set_entry_point(self, name: str) -> None:
        self.entry_point = name

    def compile(self):
        return CompiledGraph(self)

class CompiledGraph:
    def __init__(self, graph: StateGraph):
        self.graph = graph

    async def ainvoke(self, state: ConversationState, db: Any = None) -> ConversationState:
        """Asynchronously executes graph nodes sequentially from the entrypoint."""
        current = self.graph.entry_point
        logger.info(f"Starting state machine execution at entry node: {current}")
        
        loop_count = 0
        max_loops = 50
        
        while current and current != END:
            loop_count += 1
            if loop_count > max_loops:
                logger.error("State machine exceeded safety execution limit of 50 loops.")
                break
                
            logger.info(f"Executing node: {current}")
            node_func = self.graph.nodes.get(current)
            if not node_func:
                logger.error(f"Node '{current}' is defined in edges but function is missing.")
                break
            
            # Execute node
            state = await node_func(state, db=db)
            
            # Determine next node
            next_node = None
            if current in self.graph.edges:
                next_node = self.graph.edges[current]
                logger.info(f"Transitioning from '{current}' to '{next_node}' via static edge")
            elif current in self.graph.conditional_edges:
                routing_func, mapping = self.graph.conditional_edges[current]
                decision = routing_func(state)
                next_node = mapping.get(decision)
                logger.info(f"Transitioning from '{current}' to '{next_node}' via conditional decision: '{decision}'")
            else:
                logger.info(f"No outgoing edges from node '{current}'. Terminating flow.")
                break
                
            current = next_node
            
        logger.info("Finished state machine execution.")
        return state

def should_escalate_to_deepseek_r1(state: ConversationState) -> str:
    """
    Evaluates whether to route to DeepSeek-R1 (671B CoT clinical reasoner)
    or proceed directly to fast conversational generation.
    """
    # Trigger 1: Multimodal image or lab document uploaded
    if state.get("multimodal_data"):
        logger.info("Escalation Gate: Multimodal data detected -> DeepSeek-R1")
        return "deep_reasoning"
        
    # Trigger 2: Multi-system symptom cluster or high severity
    symptoms = state.get("symptoms", [])
    if len(symptoms) >= 2 or any(s.severity and s.severity >= 7 for s in symptoms):
        logger.info("Escalation Gate: High severity or multi-system symptom -> DeepSeek-R1")
        return "deep_reasoning"
        
    # Trigger 3: Persistent complaint or therapy failure
    last_turn = next((t["content"].lower() for t in reversed(state.get("turns", [])) if t["role"] == "user"), "")
    if any(k in last_turn for k in ["worse", "not working", "fever since 3 days", "3 din se", "ulti nahi ruk rahi"]):
        logger.info("Escalation Gate: Treatment failure / persistent chronicity -> DeepSeek-R1")
        return "deep_reasoning"
        
    return "generate"

def build_graph() -> CompiledGraph:
    """Build and compile the conversational triage workflow graph with Gated Deep Reasoning."""
    g = StateGraph(ConversationState)

    g.add_node("intake", intake.run)
    g.add_node("collect_symptoms", symptom_collector.run)
    g.add_node("safety_check", safety_check.run)
    g.add_node("retrieve", retrieve.run)
    g.add_node("deep_reasoning", deep_reasoning.run)
    g.add_node("generate", generate.run)
    g.add_node("triage", triage_router.run)

    g.set_entry_point("intake")
    g.add_edge("intake", "collect_symptoms")
    g.add_edge("collect_symptoms", "safety_check")

    # Safety check routing logic: emergency short-circuits straight to the END
    g.add_conditional_edges(
        "safety_check",
        lambda s: "emergency" if s["red_flag_detected"] else "continue",
        {"emergency": END, "continue": "retrieve"},
    )

    # Gated Deep Reasoning escalation edge
    g.add_conditional_edges(
        "retrieve",
        should_escalate_to_deepseek_r1,
        {"deep_reasoning": "deep_reasoning", "generate": "generate"}
    )

    g.add_edge("deep_reasoning", "generate")
    g.add_edge("generate", "triage")
    g.add_edge("triage", END)

    return g.compile()
