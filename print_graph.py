"""
Print/Visualize the Super-Graph structure
"""

from orchestration.super_graph import create_super_graph


def print_graph():
    """Print the super-graph in various formats"""
    
    # Create the graph (uncompiled to get the structure)
    workflow = create_super_graph()
    graph = workflow.compile()
    
    print("=" * 60)
    print("SUPER-GRAPH STRUCTURE")
    print("=" * 60)
    
    # ASCII representation
    print("\n📊 ASCII Graph:\n")
    try:
        graph.get_graph().print_ascii()
    except Exception as e:
        print(f"ASCII print not available: {e}")
    
    # Mermaid diagram (can be rendered in markdown viewers)
    print("\n" + "=" * 60)
    print("📈 Mermaid Diagram (paste into mermaid live editor):")
    print("=" * 60 + "\n")
    try:
        mermaid = graph.get_graph().draw_mermaid()
        print(mermaid)
    except Exception as e:
        print(f"Mermaid generation not available: {e}")
    
    # Save as PNG using pygraphviz or graphviz
    print("\n" + "=" * 60)
    print("💾 Saving graph image...")
    print("=" * 60 + "\n")
    
    try:
        # Try using graphviz directly (requires: pip install graphviz, and Graphviz installed on system)
        png_data = graph.get_graph().draw_png()
        with open("super_graph.png", "wb") as f:
            f.write(png_data)
        print("✅ Graph saved as 'super_graph.png'")
    except Exception as e1:
        print(f"⚠️  Graphviz method failed: {e1}")
        
        # Fallback: save mermaid to file and use matplotlib
        try:
            save_graph_with_matplotlib(graph)
        except Exception as e2:
            print(f"⚠️  Matplotlib method failed: {e2}")
            
            # Last resort: save mermaid to .md file
            try:
                mermaid = graph.get_graph().draw_mermaid()
                with open("super_graph.md", "w") as f:
                    f.write("# Super-Graph Diagram\n\n")
                    f.write("```mermaid\n")
                    f.write(mermaid)
                    f.write("\n```\n")
                print("✅ Mermaid diagram saved as 'super_graph.md'")
                print("   Open in VS Code with Mermaid extension or paste into mermaid.live")
            except Exception as e3:
                print(f"❌ All methods failed: {e3}")


def save_graph_with_matplotlib(graph):
    """Save graph using matplotlib and networkx"""
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    
    # Get the graph structure
    lg = graph.get_graph()
    
    # Extract nodes and edges
    nodes = list(lg.nodes)
    edges = [(e.source, e.target) for e in lg.edges]
    
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    # Define node positions manually for this specific graph
    positions = {
        "__start__": (0.5, 1.0),
        "classify_intent": (0.5, 0.9),
        "invoke_email_agent": (0.1, 0.7),
        "invoke_meeting_agent": (0.25, 0.7),
        "invoke_task_agent": (0.4, 0.7),
        "invoke_wellness_agent": (0.55, 0.7),
        "invoke_followup_agent": (0.7, 0.7),
        "invoke_report_agent": (0.85, 0.7),
        "invoke_briefing": (0.15, 0.55),
        "handle_chat": (0.85, 0.55),
        "check_cross_agent_triggers": (0.5, 0.4),
        "execute_triggers": (0.3, 0.25),
        "generate_response": (0.7, 0.25),
        "record_episode": (0.5, 0.1),
        "__end__": (0.5, 0.0),
    }
    
    # Draw edges
    for source, target in edges:
        if source in positions and target in positions:
            x1, y1 = positions[source]
            x2, y2 = positions[target]
            ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                       arrowprops=dict(arrowstyle="->", color="gray", lw=1.5))
    
    # Draw nodes
    node_colors = {
        "__start__": "#90EE90",
        "__end__": "#FFB6C1",
        "classify_intent": "#87CEEB",
        "check_cross_agent_triggers": "#DDA0DD",
        "execute_triggers": "#F0E68C",
        "generate_response": "#98FB98",
        "record_episode": "#E6E6FA",
    }
    
    for node in nodes:
        if node in positions:
            x, y = positions[node]
            color = node_colors.get(node, "#ADD8E6")
            bbox = dict(boxstyle="round,pad=0.3", facecolor=color, edgecolor="black", linewidth=2)
            ax.text(x, y, node.replace("_", "\n"), ha="center", va="center", 
                   fontsize=8, fontweight="bold", bbox=bbox)
    
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Super-Graph: Multi-Agent Orchestration", fontsize=14, fontweight="bold", pad=20)
    
    plt.tight_layout()
    plt.savefig("super_graph.png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("✅ Graph saved as 'super_graph.png' using matplotlib")


if __name__ == "__main__":
    print_graph()
