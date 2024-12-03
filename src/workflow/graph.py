from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from ..models.research_models import MarketResearchState
from ..services.document_service import DocumentService
from .nodes import WorkflowNodes

class ResearchWorkflow:
    def __init__(self):
        self.nodes = WorkflowNodes()
        self.document_service = DocumentService()
        self.workflow = self._create_workflow()

    async def export_data(self, state):
        """Export data to Excel and return updated state."""
        filename = await self.document_service.save_to_excel(state["companies"])
        return {**state, "output_file": filename}

    def _create_workflow(self):
        workflow = StateGraph(MarketResearchState)
        
        workflow.add_node("generate_search_terms", self.nodes.generate_search_terms)
        workflow.add_node("gather_company_data", self.nodes.gather_company_data)
        workflow.add_node("export_report", self.export_data)

        workflow.add_edge(START, "generate_search_terms")
        workflow.add_edge("generate_search_terms", "gather_company_data")
        workflow.add_edge("gather_company_data", "export_report")
        workflow.add_edge("export_report", END)

        return workflow.compile(checkpointer=MemorySaver()) 