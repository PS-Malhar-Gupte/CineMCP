"""
Evaluation engine for the agent.

Provides an extensible framework to evaluate agent responses against
user queries. Implements Relevance, Confidence, Precision, and Similarity
metrics using LLM-as-a-judge.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import asyncio
from pydantic import BaseModel
from agent.llm_client import get_llm_provider, _extract_first_json
from agent.config import MODEL_NAME


class EvaluationScore(BaseModel):
    score: float


class Metric(ABC):
    """Abstract base class for all evaluation metrics."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the metric."""
        pass
        
    @abstractmethod
    async def evaluate(self, user_query: str, agent_response: str, context: Optional[str] = None) -> float:
        """
        Evaluate the agent response against the query.
        Returns a score between 0.0 and 1.0.
        """
        pass


class LLMMetric(Metric):
    """Base class for metrics that use an LLM as a judge."""
    
    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self.provider = get_llm_provider(model_name)
        
    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """The prompt template used for scoring. Should ask for JSON {"score": float}."""
        pass
        
    async def evaluate(self, user_query: str, agent_response: str, context: Optional[str] = None) -> float:
        prompt = self.prompt_template.format(
            query=user_query,
            response=agent_response,
            context=context or "No additional context provided."
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        def run_llm():
            return self.provider.call(messages)
            
        try:
            result = await asyncio.to_thread(run_llm)
            parsed = _extract_first_json(result)
            score_data = EvaluationScore.model_validate(parsed)
            # Ensure score is between 0 and 1
            return max(0.0, min(1.0, score_data.score))
        except Exception as e:
            print(f"Error evaluating {self.name}: {e}")
            return 0.0


class RelevanceMetric(LLMMetric):
    @property
    def name(self) -> str:
        return "relevance"
        
    @property
    def prompt_template(self) -> str:
        return (
            "Evaluate how relevant the agent's response is to the user's query.\n"
            "Query: {query}\n"
            "Response: {response}\n\n"
            "Respond ONLY with a JSON object in this format: {{\"score\": <float between 0.0 and 1.0>}}\n"
            "0.0 means completely irrelevant, 1.0 means perfectly relevant."
        )


class ConfidenceMetric(LLMMetric):
    @property
    def name(self) -> str:
        return "confidence"
        
    @property
    def prompt_template(self) -> str:
        return (
            "Evaluate the confidence level of the agent's response.\n"
            "Does it sound certain, or does it use hedge words (e.g., 'might', 'probably', 'I think')?\n"
            "Query: {query}\n"
            "Response: {response}\n\n"
            "Respond ONLY with a JSON object in this format: {{\"score\": <float between 0.0 and 1.0>}}\n"
            "0.0 means completely unsure or apologetic, 1.0 means highly confident and authoritative."
        )


class PrecisionMetric(LLMMetric):
    @property
    def name(self) -> str:
        return "precision"
        
    @property
    def prompt_template(self) -> str:
        return (
            "Evaluate the precision of the agent's response.\n"
            "Does it directly answer the query without unnecessary fluff or rambling?\n"
            "Query: {query}\n"
            "Response: {response}\n\n"
            "Respond ONLY with a JSON object in this format: {{\"score\": <float between 0.0 and 1.0>}}\n"
            "0.0 means bloated or off-target, 1.0 means exact and concise."
        )


class SimilarityMetric(LLMMetric):
    @property
    def name(self) -> str:
        return "similarity"
        
    @property
    def prompt_template(self) -> str:
        return (
            "Evaluate the semantic similarity between the core intent of the query and the response.\n"
            "Query: {query}\n"
            "Response: {response}\n\n"
            "Respond ONLY with a JSON object in this format: {{\"score\": <float between 0.0 and 1.0>}}\n"
            "0.0 means conceptually disjoint, 1.0 means they align perfectly in topic and intent."
        )


class EvaluationEngine:
    """Runs a suite of metrics against a query and response."""
    
    def __init__(self, metrics: Optional[List[Metric]] = None):
        if metrics is None:
            self.metrics = [
                RelevanceMetric(),
                ConfidenceMetric(),
                PrecisionMetric(),
                SimilarityMetric()
            ]
        else:
            self.metrics = metrics
            
    def add_metric(self, metric: Metric) -> None:
        """Easily add new metrics to the evaluation engine."""
        self.metrics.append(metric)
        
    async def evaluate_all(self, user_query: str, agent_response: str, context: Optional[str] = None) -> Dict[str, float]:
        """Runs all metrics concurrently and returns a dictionary of scores."""
        tasks = [
            metric.evaluate(user_query, agent_response, context)
            for metric in self.metrics
        ]
        
        results = await asyncio.gather(*tasks)
        
        return {
            metric.name: score 
            for metric, score in zip(self.metrics, results)
        }
