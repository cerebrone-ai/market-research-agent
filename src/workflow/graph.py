from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from ..models.research_models import MarketResearchState
from .nodes import WorkflowNodes

class ResearchWorkflow:
    def __init__(self):
        self.nodes = WorkflowNodes()
        self.workflow = self._create_workflow()

    def _create_workflow(self):
        workflow = StateGraph(MarketResearchState)
        
        workflow.add_node("generate_search_terms", self.nodes.generate_search_terms)
        workflow.add_node("gather_company_data", self.nodes.gather_company_data)

        workflow.add_edge(START, "generate_search_terms")
        workflow.add_edge("generate_search_terms", "gather_company_data")
        workflow.add_edge("gather_company_data", END)

        return workflow.compile(checkpointer=MemorySaver()) 