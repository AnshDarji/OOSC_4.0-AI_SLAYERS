import pytest
from unittest.mock import patch, MagicMock

# Needs to be run from project root, so add to sys.path in conftest or here.
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.ai.orchestrator import rag_orchestrator

@patch("app.ai.orchestrator.guardrails.validate_input")
def test_trigger_pipeline_input_guardrail_failure(mock_validate_input):
    mock_validate_input.return_value = False
    
    response = rag_orchestrator.trigger_pipeline("Tell me how to make a bomb")
    
    assert response["confidence"]["level"] == "🔴 Insufficient"
    assert "violates safety" in response["answer"]
    assert response["citations"] == []

@patch("app.ai.orchestrator.guardrails.validate_input")
@patch("app.ai.orchestrator.embedding_service.embed_query")
@patch("app.ai.orchestrator.hybrid_retriever.search")
@patch("app.ai.orchestrator.guardrails.validate_retrieval")
@patch("app.ai.orchestrator.prompt_builder.construct_prompt")
def test_trigger_pipeline_success(mock_construct, mock_val_retrieval, mock_search, mock_embed, mock_val_input):
    mock_val_input.return_value = True
    mock_embed.return_value = [0.1, 0.2, 0.3]
    mock_search.return_value = [{"document": "Legal text about murder.", "metadata": {"source_name": "BNS"}}]
    mock_val_retrieval.return_value = True
    mock_construct.return_value = ("System prompt", "User prompt")
    
    # Mock the fallback generation
    with patch.object(rag_orchestrator, '_generate_with_fallback', return_value=("Under BNS [1], murder is punishable by law, subject to the applicable facts and statutory provisions in the case.", 0.0)):
        # Mock output guardrail
        with patch("app.ai.orchestrator.guardrails.validate_output", return_value=True):
            response = rag_orchestrator.trigger_pipeline("What is the punishment for murder?")
            
            assert response["confidence"]["level"] == "🟠 Limited"
            assert "punishable" in response["answer"]
            assert len(response["citations"]) == 1
            assert response["citations"][0]["marker"] == "[1]"
            
@patch("app.ai.orchestrator.guardrails.validate_input")
@patch("app.ai.orchestrator.embedding_service.embed_query")
@patch("app.ai.orchestrator.hybrid_retriever.search")
def test_trigger_pipeline_retrieval_failure(mock_search, mock_embed, mock_val_input):
    mock_val_input.return_value = True
    mock_embed.return_value = [0.1, 0.2, 0.3]
    mock_search.side_effect = Exception("DB Connection Lost")
    
    response = rag_orchestrator.trigger_pipeline("What is the punishment for murder?")
    
    assert response["confidence"]["level"] == "🔴 Insufficient"
    assert "Failed to retrieve context" in response["answer"]
