'''
This module defines the DAG : Directed Acyclic Graph for the workflow of the compliance QA pipeline that orchestrates the processing of video compliance audit process.
It connects the nodes using stateGraphs from Langgraph
START -> index_video_node -> audit_content_node -> generate_report_node -> END
'''
from langgraph.graph import StateGraph, END
from backend.src.graph.state import VideoAuditState
from backend.src.graph.nodes import (
     index_video_node,
     compliance_audit_node
)

def create_graph():
    '''
    Constructs and compile the langgraph workflow
    Returns :
    Compiled Graph: runnable graph objects for execution
    '''
    # initialize the graph with state schema
    workflow = StateGraph(VideoAuditState)
    # add the nodes
    workflow.add_node("indexer", index_video_node)
    workflow.add_node("auditor",compliance_audit_node)
    # defines the entry points : indexer
    workflow.set_entry_point("indexer")
    # define the edges
    workflow.add_edge("indexer", "auditor")
    # once the audit is completed, the workflow ends
    workflow.add_edge("auditor", END)
    # compile the graph
    app = workflow.compile()
    return app

# expose this runnable app
app = create_graph()