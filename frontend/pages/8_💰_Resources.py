"""
Resource Economy Dashboard for AgriMesh Autonomous

Visualize resource allocation, bidding history, and decision logs.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.orchestration.orchestrator import create_orchestrator
from src.orchestration.bidding import ResourceBid, BidStatus
from src.orchestration.resource_economy import Priority as ResourcePriority
from src.common.decision_logger import DecisionLogger

st.set_page_config(
    page_title="Resource Economy | AgriMesh",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Resource Economy Dashboard")
st.markdown("Monitor resource allocation, agent bidding, and decision history")

# Initialize session state
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = create_orchestrator(
        farm_id="demo-farm",
        water_capacity=100000,
        labour_hours=80,
        daily_budget=1000,
        enable_logging=True
    )

orch = st.session_state.orchestrator

# Sidebar: Resource Configuration
st.sidebar.header("⚙️ Resource Configuration")

water_capacity = st.sidebar.number_input(
    "Water Capacity (L/day)",
    min_value=1000,
    max_value=500000,
    value=100000,
    step=5000
)

labour_hours = st.sidebar.number_input(
    "Labour Hours (h/day)",
    min_value=8,
    max_value=200,
    value=80,
    step=8
)

daily_budget = st.sidebar.number_input(
    "Daily Budget (USD)",
    min_value=100,
    max_value=10000,
    value=1000,
    step=100
)

if st.sidebar.button("Apply Configuration"):
    orch.configure_resources(
        water_liters=water_capacity,
        labour_hours=labour_hours,
        daily_budget=daily_budget
    )
    st.sidebar.success("✓ Configuration applied")

if st.sidebar.button("Reset Daily Resources"):
    orch.reset_daily_resources()
    st.sidebar.success("✓ Resources reset to full capacity")

# Main content
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Resource Status", 
    "🎯 Submit Bid", 
    "📜 Bid History",
    "📈 Decision Analytics"
])

# Tab 1: Resource Status
with tab1:
    st.header("Current Resource Pool")
    
    status = orch.get_resource_status()
    
    # Resource gauges
    col1, col2, col3, col4 = st.columns(4)
    
    resources = status.get("resources", {})
    
    for col, (name, data) in zip(
        [col1, col2, col3, col4],
        list(resources.items())[:4]
    ):
        with col:
            available = data["available"]
            total = data["total"]
            pct = (available / total * 100) if total > 0 else 0
            
            # Color based on availability
            if pct > 60:
                color = "green"
            elif pct > 30:
                color = "orange"
            else:
                color = "red"
            
            st.metric(
                label=name.title(),
                value=f"{available:,.0f} {data['unit']}",
                delta=f"{pct:.0f}% available"
            )
            
            # Progress bar
            st.progress(pct / 100)
    
    # Resource utilization chart
    st.subheader("Resource Utilization")
    
    util_data = []
    for name, data in resources.items():
        total = data["total"]
        available = data["available"]
        used = total - available
        util_data.append({
            "Resource": name.title(),
            "Used": used,
            "Available": available,
            "Utilization": data["utilization"]
        })
    
    df_util = pd.DataFrame(util_data)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Used",
        x=df_util["Resource"],
        y=df_util["Used"],
        marker_color="indianred"
    ))
    fig.add_trace(go.Bar(
        name="Available",
        x=df_util["Resource"],
        y=df_util["Available"],
        marker_color="lightgreen"
    ))
    fig.update_layout(barmode="stack", title="Resource Allocation")
    st.plotly_chart(fig, use_container_width=True)
    
    # Active allocations
    st.subheader("Active Allocations")
    active = orch.resource_pool.active_allocations
    if active:
        alloc_data = []
        for alloc in active:
            alloc_data.append({
                "ID": alloc.allocation_id,
                "Agent": alloc.request.agent_id,
                "Resource": alloc.request.resource_type,
                "Quantity": alloc.quantity_allocated,
                "Priority": alloc.request.priority,
                "Status": alloc.status
            })
        st.dataframe(pd.DataFrame(alloc_data), use_container_width=True)
    else:
        st.info("No active allocations")

# Tab 2: Submit Bid
with tab2:
    st.header("Submit Resource Bid")
    st.markdown("Manually submit a resource request on behalf of an agent")
    
    col1, col2 = st.columns(2)
    
    with col1:
        agent_name = st.selectbox(
            "Agent",
            ["Irrigation Agent", "Livestock Agent", "Maintenance Agent", "Security Agent", "Custom"]
        )
        
        if agent_name == "Custom":
            agent_name = st.text_input("Custom Agent Name")
        
        resource_type = st.selectbox(
            "Resource Type",
            ["water", "labour", "budget", "feed", "electricity"]
        )
        
        quantity = st.number_input(
            "Quantity Requested",
            min_value=1.0,
            value=1000.0,
            step=100.0
        )
        
        min_quantity = st.number_input(
            "Minimum Acceptable",
            min_value=0.0,
            max_value=quantity,
            value=quantity * 0.5,
            step=100.0
        )
    
    with col2:
        priority = st.selectbox(
            "Priority",
            ["Normal", "High", "Urgent", "Welfare", "Critical"]
        )
        
        priority_map = {
            "Normal": ResourcePriority.NORMAL,
            "High": ResourcePriority.HIGH,
            "Urgent": ResourcePriority.URGENT,
            "Welfare": ResourcePriority.WELFARE,
            "Critical": ResourcePriority.CRITICAL
        }
        
        flexible = st.checkbox("Flexible Timing (can be delayed)")
        
        reason = st.text_area(
            "Reason/Justification",
            placeholder="Why is this resource needed?"
        )
        
        risk_if_denied = st.text_input(
            "Risk if Denied",
            placeholder="What happens if this request is rejected?"
        )
    
    if st.button("Submit Bid", type="primary"):
        bid = ResourceBid(
            agent_id=agent_name.lower().replace(" ", "-"),
            agent_name=agent_name,
            resource_type=resource_type,
            quantity_requested=quantity,
            quantity_minimum=min_quantity,
            priority=priority_map[priority],
            flexible_timing=flexible,
            reason=reason or f"Manual bid for {resource_type}",
            risk_if_denied=risk_if_denied or "Not specified"
        )
        
        bid_id = orch.submit_manual_bid(bid)
        st.success(f"✓ Bid submitted: {bid_id}")
        
        # Resolve immediately
        resolved = orch.force_resolve_bids()
        if resolved:
            result = resolved[0]
            if result.status == BidStatus.ACCEPTED:
                st.success(f"✅ Bid ACCEPTED: {result.allocated_quantity} {resource_type}")
            elif result.status == BidStatus.PARTIAL:
                st.warning(f"⚠️ Partial allocation: {result.allocated_quantity}/{quantity}")
            elif result.status == BidStatus.REJECTED:
                st.error(f"❌ Bid REJECTED: {result.response_message}")
            else:
                st.info(f"ℹ️ Status: {result.status.value}")

# Tab 3: Bid History
with tab3:
    st.header("Bid Resolution History")
    
    resolved_bids = orch.bidding_engine.resolved_bids
    
    if resolved_bids:
        history_data = []
        for bid in reversed(resolved_bids[-50:]):  # Last 50
            history_data.append({
                "Bid ID": bid.bid_id,
                "Agent": bid.agent_name,
                "Resource": bid.resource_type,
                "Requested": bid.quantity_requested,
                "Allocated": bid.allocated_quantity,
                "Priority": bid.priority,
                "Status": bid.status.value,
                "Response": bid.response_message[:50] + "..." if len(bid.response_message) > 50 else bid.response_message,
                "Submitted": bid.submitted_at.strftime("%H:%M:%S") if bid.submitted_at else "-"
            })
        
        df_history = pd.DataFrame(history_data)
        
        # Status summary
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            accepted = sum(1 for b in resolved_bids if b.status == BidStatus.ACCEPTED)
            st.metric("Accepted", accepted)
        with col2:
            partial = sum(1 for b in resolved_bids if b.status == BidStatus.PARTIAL)
            st.metric("Partial", partial)
        with col3:
            rejected = sum(1 for b in resolved_bids if b.status == BidStatus.REJECTED)
            st.metric("Rejected", rejected)
        with col4:
            queued = sum(1 for b in resolved_bids if b.status == BidStatus.QUEUED)
            st.metric("Queued", queued)
        
        # History table
        st.dataframe(
            df_history,
            use_container_width=True,
            column_config={
                "Status": st.column_config.TextColumn(
                    "Status",
                    help="Bid resolution status"
                )
            }
        )
        
        # Status distribution chart
        status_counts = df_history["Status"].value_counts()
        fig = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="Bid Status Distribution",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.info("No bids have been resolved yet. Submit a bid to see history.")

# Tab 4: Decision Analytics
with tab4:
    st.header("Decision Analytics")
    
    try:
        logger = DecisionLogger("farm_os/logs/decisions.db")
        
        # Daily summary
        summary = logger.get_daily_summary()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Today's Summary")
            st.metric("Total Decisions", summary.get("total_decisions", 0))
            
            by_agent = summary.get("by_agent", {})
            if by_agent:
                agent_df = pd.DataFrame([
                    {"Agent": k, "Count": v["count"], "Success": v["success"]}
                    for k, v in by_agent.items()
                ])
                st.dataframe(agent_df, use_container_width=True)
        
        with col2:
            st.subheader("By Decision Type")
            by_type = summary.get("by_type", {})
            if by_type:
                fig = px.bar(
                    x=list(by_type.keys()),
                    y=list(by_type.values()),
                    labels={"x": "Type", "y": "Count"},
                    title="Decisions by Type"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Recent decisions
        st.subheader("Recent Decisions")
        recent = logger.query(limit=20)
        
        if recent:
            recent_data = []
            for d in recent:
                recent_data.append({
                    "ID": d.decision_id[:12],
                    "Agent": d.agent_name,
                    "Type": d.decision_type,
                    "Action": d.action,
                    "Success": "✓" if d.success else "✗",
                    "Time": d.timestamp.strftime("%H:%M:%S")
                })
            st.dataframe(pd.DataFrame(recent_data), use_container_width=True)
        else:
            st.info("No decisions logged yet")
            
    except Exception as e:
        st.warning(f"Could not load decision analytics: {e}")
        st.info("Run an orchestrator cycle to generate decision data")

# Footer
st.markdown("---")
st.markdown(
    "**AgriMesh Autonomous** | Phase 5: Resource Economy | "
    f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
)
