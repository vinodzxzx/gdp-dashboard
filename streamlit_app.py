import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Set the page configuration
st.set_page_config(
    page_title='Revenue Analytics for Valley',
    page_icon=':chart_with_upwards_trend:',
    layout='wide'
)

# -----------------------------------------------------------------------------
# Data Loading and Parsing

@st.cache_data
def load_data():
    DATA_FILENAME = Path(__file__).parent/'data/revenue1.csv'
    # Read the raw CSV without headers first to handle the complex structure
    raw_df = pd.read_csv(DATA_FILENAME, header=None)
    
    # --- 1. Department Summary (Pre/Post RC) ---
    # Rows 25-31 (0-indexed: 24-30), Cols 0, 1, 3
    dept_summary_df = raw_df.iloc[24:31, [0, 1, 3]].copy()
    dept_summary_df.columns = ['Department', 'Pre_RC_RVU', 'Post_RC_RVU']
    # Filter out empty rows and Grand Total
    dept_summary_df = dept_summary_df[dept_summary_df['Department'].notna()]
    dept_summary_df = dept_summary_df[dept_summary_df['Department'] != 'Grand Total']
    
    # Convert to numeric
    dept_summary_df['Pre_RC_RVU'] = pd.to_numeric(dept_summary_df['Pre_RC_RVU'], errors='coerce')
    dept_summary_df['Post_RC_RVU'] = pd.to_numeric(dept_summary_df['Post_RC_RVU'], errors='coerce')
    
    
    # --- 2. E&M Level Breakdown (General) ---
    # Rows 3-21 approx (cols 0-4)
    em_df = raw_df.iloc[2:22, 0:5].copy()
    em_df.columns = ['Category', 'Pre_RVU', 'Pre_Pct', 'Post_RVU', 'Post_Pct']
    # Filter out empty categories
    em_df = em_df[em_df['Category'].notna()]
    
    # Convert numeric columns
    for col in ['Pre_RVU', 'Post_RVU']:
        em_df[col] = pd.to_numeric(em_df[col], errors='coerce')
    
    
    # --- 3. Detailed Breakdown (Right side of CSV) ---
    # Cols 6-9 (G-J)
    detail_df = raw_df.iloc[2:73, 6:10].copy()
    detail_df.columns = ['Department', 'Service', 'Avg_Adj_Total_RVU', 'Count_Pct']
    
    # Forward fill the Department column as it is sparse
    detail_df['Department'] = detail_df['Department'].ffill()
    
    # Clean up
    detail_df = detail_df[detail_df['Service'].notna()]
    # Remove 'Total' rows
    detail_df = detail_df[~detail_df['Service'].astype(str).str.contains('Total', case=False)]
    detail_df = detail_df[~detail_df['Department'].astype(str).str.contains('Total', case=False)]
    
    # Convert numeric
    detail_df['Avg_Adj_Total_RVU'] = pd.to_numeric(detail_df['Avg_Adj_Total_RVU'], errors='coerce')
    
    return dept_summary_df, em_df, detail_df

try:
    dept_summary, em_breakdown, detail_data = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# Dashboard Layout

st.title("Revenue Analytics for Valley")
st.markdown("### Pre-RC vs Post-RC Analysis")

# Top Level Metrics
col1, col2, col3 = st.columns(3)

total_pre = dept_summary['Pre_RC_RVU'].sum()
total_post = dept_summary['Post_RC_RVU'].sum()
improvement = ((total_post - total_pre) / total_pre) * 100 if total_pre != 0 else 0

col1.metric("Total Pre-RC RVU", f"{total_pre:.2f}")
col2.metric("Total Post-RC RVU", f"{total_post:.2f}")
col3.metric("Overall Improvement", f"{improvement:.2f}%", delta_color="normal")

st.divider()

# --- Chart 1: Department Comparison ---
st.subheader("RVU Performance by Department")

# Melt for easy plotting
dept_melted = dept_summary.melt(id_vars='Department', value_vars=['Pre_RC_RVU', 'Post_RC_RVU'], var_name='Type', value_name='RVU')
dept_melted['Type'] = dept_melted['Type'].replace({'Pre_RC_RVU': 'Pre RC', 'Post_RC_RVU': 'Post RC'})

fig_dept = px.bar(
    dept_melted, 
    x='Department', 
    y='RVU', 
    color='Type', 
    barmode='group',
    title="Average RVU by Department (Pre vs Post)",
    color_discrete_map={'Pre RC': '#EF553B', 'Post RC': '#636EFA'}
)
st.plotly_chart(fig_dept, use_container_width=True)

# --- Chart 2: Detailed Drilldown ---
st.divider()
st.subheader("Department Deep Dive")

# Get list of departments for dropdown
dept_list = sorted(detail_data['Department'].unique().astype(str))
selected_dept = st.selectbox("Select Department to Analyze", dept_list)

if selected_dept:
    filtered_data = detail_data[detail_data['Department'] == selected_dept].sort_values('Avg_Adj_Total_RVU', ascending=True)
    
    fig_drill = px.bar(
        filtered_data,
        x='Avg_Adj_Total_RVU',
        y='Service',
        orientation='h',
        title=f"Average Adjusted Total RVU by Service - {selected_dept}",
        labels={'Avg_Adj_Total_RVU': 'Average RVU', 'Service': 'Service/Level'},
        height=max(400, len(filtered_data) * 20)
    )
    st.plotly_chart(fig_drill, use_container_width=True)

# --- Chart 3: E&M Breakdown ---
st.divider()
st.subheader("E&M Level & Procedure Breakdown")

tab1, tab2 = st.tabs(["RVU Comparison", "Percentage Change"])

with tab1:
    # Filter only significant RVU contributors for cleaner chart
    em_rvu_chart = em_breakdown[em_breakdown['Pre_RVU'] > 0.01].sort_values('Post_RVU', ascending=False)
    
    fig_em = go.Figure()
    fig_em.add_trace(go.Bar(name='Pre RC', x=em_rvu_chart['Category'], y=em_rvu_chart['Pre_RVU']))
    fig_em.add_trace(go.Bar(name='Post RC', x=em_rvu_chart['Category'], y=em_rvu_chart['Post_RVU']))
    fig_em.update_layout(barmode='group', title="RVU Comparison by Procedure Category")
    st.plotly_chart(fig_em, use_container_width=True)

with tab2:
    st.dataframe(em_breakdown[['Category', 'Pre_RVU', 'Post_RVU', 'Pre_Pct', 'Post_Pct']], hide_index=True)
