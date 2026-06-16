import networkx as nx
from typing import Dict, List, Any

class GraphService:
    @staticmethod
    def build_supply_chain_graph() -> nx.DiGraph:
        """
        Builds a directed graph of the eyewear company's supply chain:
        Nodes: Stores, Main Lab, Vendors, Shipping Hubs
        Edges: Sourcing/delivery paths with weights for SLA days, costs, and reliability.
        """
        G = nx.DiGraph()
        
        # 1. Add nodes
        # Production & Sourcing
        G.add_node("Main Lab", type="production", capacity=500)
        G.add_node("Vendor A (Premium)", type="vendor", capacity=200, reliability=0.98)
        G.add_node("Vendor B (Economy)", type="vendor", capacity=300, reliability=0.85)
        G.add_node("Logistics Hub North", type="hub")
        G.add_node("Logistics Hub South", type="hub")
        
        # Retail Stores
        stores = [f"Store {i}" for i in range(1, 11)]
        for s in stores:
            G.add_node(s, type="store")
            
        # 2. Add edges with parameters (lead_time_hours, transport_cost, reliability)
        # Sourcing
        G.add_edge("Vendor A (Premium)", "Main Lab", lead_time=24, cost=150, reliability=0.98)
        G.add_edge("Vendor B (Economy)", "Main Lab", lead_time=48, cost=75, reliability=0.85)
        
        # Distribution to Hubs
        G.add_edge("Main Lab", "Logistics Hub North", lead_time=12, cost=50, reliability=0.95)
        G.add_edge("Main Lab", "Logistics Hub South", lead_time=18, cost=60, reliability=0.92)
        
        # Hubs to Stores
        # Stores 1-5 connected to North
        for i in range(1, 6):
            G.add_edge("Logistics Hub North", f"Store {i}", lead_time=12, cost=30, reliability=0.97)
        # Stores 6-10 connected to South
        for i in range(6, 11):
            G.add_edge("Logistics Hub South", f"Store {i}", lead_time=16, cost=40, reliability=0.94)
            
        return G

    @staticmethod
    def analyze_bottlenecks() -> Dict[str, Any]:
        """
        Analyze network bottlenecks using node betweenness centrality and critical vendor checks.
        """
        G = GraphService.build_supply_chain_graph()
        
        # 1. Betweenness Centrality (identifies nodes that control flow)
        centrality = nx.betweenness_centrality(G, weight="lead_time")
        sorted_centrality = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        
        # 2. Shortest paths from vendors to stores
        bottlenecks = []
        for node, val in sorted_centrality[:3]:
            bottlenecks.append({
                "node": node,
                "centrality_score": round(val, 4),
                "type": G.nodes[node].get("type", "unknown")
            })
            
        # 3. Supply line reliability propagation (critical path analysis)
        critical_vendors = []
        for n, data in G.nodes(data=True):
            if data.get("type") == "vendor" and data.get("reliability", 1.0) < 0.90:
                critical_vendors.append({
                    "vendor": n,
                    "reliability": data.get("reliability"),
                    "risk": "High risk of delayed raw materials"
                })
                
        # Calculate max latency from vendors to stores
        max_latency = 0
        slowest_path = []
        for vendor in ["Vendor A (Premium)", "Vendor B (Economy)"]:
            for store in [f"Store {i}" for i in range(1, 11)]:
                try:
                    path = nx.shortest_path(G, source=vendor, target=store, weight="lead_time")
                    latency = nx.path_weight(G, path, weight="lead_time")
                    if latency > max_latency:
                        max_latency = latency
                        slowest_path = path
                except nx.NetworkXNoPath:
                    pass

        return {
            "bottlenecks": bottlenecks,
            "critical_vendors": critical_vendors,
            "system_max_lead_time_hours": max_latency,
            "slowest_supply_path": slowest_path
        }
