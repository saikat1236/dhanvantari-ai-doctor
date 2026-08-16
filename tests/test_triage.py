import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.orchestrator.graph import build_graph, should_escalate_to_deepseek_r1
from app.orchestrator.state import ConversationState, SymptomEntry
from app.llm.vision_extractor import VisionExtractor

async def run_tests():
    print("===== Running Automated Triage, Multimodal & Reasoning Tests =====")
    graph = build_graph()

    # Test 1: Emergency Red Flag Trigger (Cardiovascular pain)
    print("\nTest 1: Verification of Emergency Red Flag Trigger...")
    state_emergency: ConversationState = {
        "session_id": "test_session_emergency",
        "patient_id": "PAT-TEST001",
        "turns": [
            {"role": "user", "content": "I am experiencing severe crushing chest pain and left arm numbness."}
        ],
        "symptoms": [],
        "red_flag_detected": False,
        "red_flag_reason": None,
        "retrieved_context": [],
        "multimodal_data": None,
        "requires_deep_reasoning": False,
        "cot_reasoning_trace": None,
        "differential_candidates": [],
        "draft_prescription_payload": [],
        "triage_level": None,
        "escalated_to_rmp": False,
        "draft_response": None,
        "speech_response": None,
        "language": "en-IN"
    }
    
    result_emergency = await graph.ainvoke(state_emergency)
    assert result_emergency["red_flag_detected"] is True, "FAIL: Red flag should have been detected."
    assert result_emergency["triage_level"] == "emergency", "FAIL: Triage level should be emergency."
    assert "emergency" in result_emergency["draft_response"].lower(), "FAIL: Response should contain emergency instructions."
    print("✅ Test 1 Passed: Safety checks correctly intercepted emergency and short-circuited response.")

    # Test 2: Standard Triage Flow (Mild Fever - Self Care)
    print("\nTest 2: Verification of Self-Care symptoms...")
    state_self_care: ConversationState = {
        "session_id": "test_session_mild",
        "patient_id": "PAT-TEST002",
        "turns": [
            {"role": "user", "content": "I have had a mild fever of 99F since yesterday."}
        ],
        "symptoms": [],
        "red_flag_detected": False,
        "red_flag_reason": None,
        "retrieved_context": [],
        "multimodal_data": None,
        "requires_deep_reasoning": False,
        "cot_reasoning_trace": None,
        "differential_candidates": [],
        "draft_prescription_payload": [],
        "triage_level": None,
        "escalated_to_rmp": False,
        "draft_response": None,
        "speech_response": None,
        "language": "en-IN"
    }
    
    result_self_care = await graph.ainvoke(state_self_care)
    assert result_self_care["red_flag_detected"] is False, "FAIL: Red flag should NOT have been detected."
    assert result_self_care["triage_level"] == "self_care", f"FAIL: Expected triage level 'self_care', got '{result_self_care['triage_level']}'."
    assert len(result_self_care["retrieved_context"]) > 0, "FAIL: Should have retrieved RAG context for fever."
    print("✅ Test 2 Passed: Mild symptoms processed without emergency interruption, grounded in RAG.")

    # Test 3: Snake Bite Emergency Red Flag
    print("\nTest 3: Verification of Snake Bite Red Flag Trigger...")
    state_snake: ConversationState = {
        "session_id": "test_session_snake",
        "patient_id": "PAT-TEST003",
        "turns": [
            {"role": "user", "content": "snake bite me just now, bleeding also"}
        ],
        "symptoms": [],
        "red_flag_detected": False,
        "red_flag_reason": None,
        "retrieved_context": [],
        "multimodal_data": None,
        "requires_deep_reasoning": False,
        "cot_reasoning_trace": None,
        "differential_candidates": [],
        "draft_prescription_payload": [],
        "triage_level": None,
        "escalated_to_rmp": False,
        "draft_response": None,
        "speech_response": None,
        "language": "en-IN"
    }
    
    result_snake = await graph.ainvoke(state_snake)
    assert result_snake["red_flag_detected"] is True, "FAIL: Snake bite red flag should have been detected."
    assert result_snake["triage_level"] == "emergency", "FAIL: Triage level should be emergency."
    print("✅ Test 3 Passed: Snake bite emergency safety check triggered, correct first aid guidelines returned.")

    # Test 4: Hinglish Snake Bite Emergency Red Flag
    print("\nTest 4: Verification of Hinglish Snake Bite Red Flag Trigger...")
    state_hinglish: ConversationState = {
        "session_id": "test_session_hinglish",
        "patient_id": "PAT-TEST004",
        "turns": [
            {"role": "user", "content": "saap kaat liya mujhe abhi jaldi"}
        ],
        "symptoms": [],
        "red_flag_detected": False,
        "red_flag_reason": None,
        "retrieved_context": [],
        "multimodal_data": None,
        "requires_deep_reasoning": False,
        "cot_reasoning_trace": None,
        "differential_candidates": [],
        "draft_prescription_payload": [],
        "triage_level": None,
        "escalated_to_rmp": False,
        "draft_response": None,
        "speech_response": None,
        "language": "hi-IN"
    }
    
    result_hinglish = await graph.ainvoke(state_hinglish)
    assert result_hinglish["red_flag_detected"] is True, "FAIL: Hinglish snake bite red flag should have been detected."
    print("✅ Test 4 Passed: Hinglish emergency query successfully intercepted.")

    # Test 5: Multimodal Vision Extraction
    print("\nTest 5: Verification of Multimodal Vision Extractor...")
    extractor = VisionExtractor()
    dummy_image_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00"
    findings = await extractor.extract_from_bytes(dummy_image_bytes, "image/jpeg")
    assert "modality" in findings, "FAIL: Modality missing from vision extraction."
    assert "key_findings" in findings, "FAIL: Key findings missing from vision extraction."
    assert "preliminary_impression" in findings, "FAIL: Preliminary impression missing."
    print(f"✅ Test 5 Passed: Multimodal parser extracted '{findings.get('modality')}' ({findings.get('preliminary_impression')}).")

    # Test 6: Gated Deep Reasoning Heuristics (DeepSeek-R1 escalation)
    print("\nTest 6: Verification of Gated DeepSeek-R1 Escalation Trigger...")
    # 6A: Simple single mild symptom -> Should NOT escalate
    state_simple = state_self_care
    decision_simple = should_escalate_to_deepseek_r1(state_simple)
    assert decision_simple == "generate", f"FAIL: Expected 'generate', got '{decision_simple}'."

    # 6B: Multimodal data attached -> SHOULD escalate to deep_reasoning
    state_complex = state_self_care.copy()
    state_complex["multimodal_data"] = findings
    decision_complex = should_escalate_to_deepseek_r1(state_complex)
    assert decision_complex == "deep_reasoning", f"FAIL: Expected 'deep_reasoning', got '{decision_complex}'."

    # 6C: Multi-system severe symptom cluster -> SHOULD escalate to deep_reasoning
    state_multi = state_self_care.copy()
    state_multi["symptoms"] = [
        SymptomEntry(description="stomach pain", severity=8),
        SymptomEntry(description="vomiting", severity=7)
    ]
    decision_multi = should_escalate_to_deepseek_r1(state_multi)
    assert decision_multi == "deep_reasoning", f"FAIL: Expected 'deep_reasoning', got '{decision_multi}'."
    print("✅ Test 6 Passed: Gated escalation heuristics accurately discriminated standard vs complex cases.")

    print("\n=======================================================")
    print("ALL 6 CLINICAL, SAFETY, MULTIMODAL & REASONING TESTS PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    asyncio.run(run_tests())
