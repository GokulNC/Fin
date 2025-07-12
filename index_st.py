#!/usr/bin/env python3
"""
Beautiful Streamlit App for NIFTY Index Data
Dynamic index availability checking with elegant UI
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, date
import time
from yahoo_nifty_data import fetch_index_data, get_available_indices, fetch_all_historical_data, calculate_cagr, calculate_rolling_cagr

# Page configuration
st.set_page_config(
    page_title="📈 Indian Index Data Explorer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #1f4e79, #2e8b57);
        color: white;
        border-radius: 2px;
        margin-bottom: 1rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .success-card {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    
    .error-card {
        background: linear-gradient(135deg, #f44336 0%, #da190b 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    
    .info-card {
        background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    
    .stSelectbox > div > div {
        background-color: #f0f2f6;
        border-radius: 10px;
    }
    
    .stDateInput > div > div {
        background-color: #f0f2f6;
        border-radius: 10px;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #FF6B6B, #4ECDC4);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data()
def check_index_availability():
    """
    Check which indices are currently available via the API
    Uses current date to test availability
    """
    
    # Get all possible indices
    all_indices = get_available_indices()
    
    # Use current date for testing
    test_date = datetime.now().strftime('%d-%m-%Y')
    
    available_indices = {}
    unavailable_indices = {}
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_indices = len(all_indices)
    
    for i, (name, symbol) in enumerate(all_indices.items()):
        progress = (i + 1) / total_indices
        progress_bar.progress(progress)
        status_text.text(f"Testing {name}... ({i+1}/{total_indices})")
        
        # Test with a recent historical date (7 days ago to avoid weekend issues)
        historical_date = (datetime.now() - timedelta(days=7)).strftime('%d-%m-%Y')
        
        try:
            result = fetch_index_data(historical_date, symbol)
            if "error" not in result:
                available_indices[name] = symbol
            else:
                unavailable_indices[name] = symbol
        except Exception as e:
            unavailable_indices[name] = symbol
        
        time.sleep(0.1)  # Small delay to be respectful to API
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    return available_indices, unavailable_indices, test_date

def main():
    # Initialize ALL session state variables at the beginning
    if 'historical_data_fetched' not in st.session_state:
        st.session_state.historical_data_fetched = False
    if 'current_index' not in st.session_state:
        st.session_state.current_index = None
    if 'historical_result' not in st.session_state:
        st.session_state.historical_result = None
    if 'rolling_cagr_computed' not in st.session_state:
        st.session_state.rolling_cagr_computed = False
    if 'rolling_cagr_result' not in st.session_state:
        st.session_state.rolling_cagr_result = None
    if 'rolling_cagr_params' not in st.session_state:
        st.session_state.rolling_cagr_params = {}
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📈 Indian Index Data Explorer</h1>
        <!-- <p>Real-time Indian Stock Market Index Data</p> -->
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar for controls
    with st.sidebar:
        # Load available indices
        with st.spinner("🔍 Checking index availability..."):
            available_indices, unavailable_indices, test_date = check_index_availability()
        
        # Index selection
        st.subheader("📋 Select Index")
        if available_indices:
            selected_index_name = st.selectbox(
                "Choose an index:",
                options=list(available_indices.keys()),
                index=0,
                help="Only showing indices that are currently available"
            )
            selected_symbol = available_indices[selected_index_name]
        else:
            st.error("No indices are currently available. Please try refreshing.")
            return
        
        # Info about automatic date range
        st.subheader("📅 Data Range")
        st.info("📊 **Automatic Range**: All available historical data from the earliest date to today will be fetched.")
        
        # Submit button
        fetch_data = st.button("🚀 Fetch Complete Historical Data & Calculate CAGR", type="primary")

        st.markdown("---")
        st.subheader("📊 Availability Status")

        # Display availability stats
        total_tested = len(available_indices) + len(unavailable_indices)
        availability_percentage = len(available_indices) / total_tested * 100
        
        st.markdown(f"""
        <div class="info-card">
            <p><strong>Available:</strong> {len(available_indices)} indices</p>
            <p><strong>Unavailable:</strong> {len(unavailable_indices)} indices</p>
            <p><strong>Success Rate:</strong> {availability_percentage:.1f}%</p>
            <p><strong>Last Checked:</strong> {test_date}</p>
        </div>
        """, unsafe_allow_html=True)

        st.header("🎛️ Controls")
        
        # Check availability button
        if st.button("🔄 Refresh Index Availability", type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Check if index has changed and reset session state if needed
        if st.session_state.current_index != selected_index_name:
            st.session_state.historical_data_fetched = False
            st.session_state.current_index = selected_index_name
            st.session_state.historical_result = None
            st.session_state.rolling_cagr_computed = False
            st.session_state.rolling_cagr_result = None
            st.session_state.rolling_cagr_params = {}
        
        # Fetch data if button clicked
        if fetch_data and available_indices:
            with st.spinner(f"📊 Fetching complete historical data for {selected_index_name}..."):
                # Fetch all historical data
                result = fetch_all_historical_data(selected_symbol)
                
                # Store result in session state
                st.session_state.historical_result = result
                st.session_state.historical_data_fetched = True
        
        # Display historical data if available in session state
        if st.session_state.historical_data_fetched and st.session_state.historical_result:
            result = st.session_state.historical_result
            
            # Check if fetch was successful
            if "error" in result:
                st.markdown(f"""
                <div class="error-card">
                    <h4>❌ Error Fetching Historical Data</h4>
                    <p><strong>Index:</strong> {selected_index_name}</p>
                    <p><strong>Error:</strong> {result['error']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            else:
                # Success - display the data beautifully
                st.markdown(f"""
                <div class="success-card">
                    <h4>✅ Complete Historical Data Retrieved Successfully</h4>
                    <p><strong>Index:</strong> {selected_index_name} ({selected_symbol})</p>
                    <p><strong>Period:</strong> {result['earliest_date']} to {result['latest_date']}</p>
                    <p><strong>Duration:</strong> {result['days_diff']} days ({result['years_diff']} years)</p>
                    <p><strong>Data Points:</strong> {result['total_data_points']} trading days</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Display closing prices and CAGR in a nice layout
                col_first, col_last, col_cagr = st.columns(3)
                
                with col_first:
                    st.metric(
                        label=f"📅 First Available Price ({result['earliest_date']})",
                        value=f"₹{result['first_close']:,.2f}",
                        delta=None
                    )
                
                with col_last:
                    st.metric(
                        label=f"📅 Latest Price ({result['latest_date']})",
                        value=f"₹{result['last_close']:,.2f}",
                        delta=f"₹{result['absolute_change']:+,.2f}"
                    )
                
                with col_cagr:
                    if result['cagr'] is not None:
                        st.metric(
                            label="📈 CAGR",
                            value=f"{result['cagr']:+.2f}%",
                            delta=f"{result['percentage_change']:+.2f}% total"
                        )
                    else:
                        st.metric(
                            label="📈 CAGR",
                            value="N/A",
                            delta="Invalid data"
                        )
                
                # Display raw data summary
                with st.expander("📋 Historical Data Summary"):
                    st.write(f"**Total Data Points:** {len(result['historical_data'])} trading days")
                    st.write(f"**Data Range:** {result['earliest_date']} to {result['latest_date']}")
                    st.write(f"**First 10 Records:**")
                    st.dataframe(result['historical_data'].head(10))
                    st.write(f"**Last 10 Records:**")
                    st.dataframe(result['historical_data'].tail(10))
                
                # Add Rolling CAGR Analysis Section
                st.markdown("---")
                st.header("📊 Rolling CAGR Analysis")
                
                # Rolling CAGR Controls
                rolling_col1, rolling_col2 = st.columns(2)
                
                with rolling_col1:
                    window_years = st.slider(
                        "📅 Time Window (Years)",
                        min_value=2,
                        max_value=10,
                        value=5,
                        step=1,
                        help="Number of years for each rolling window"
                    )
                
                with rolling_col2:
                    # Get the earliest date from the fetched data for the date picker
                    earliest_available = datetime.strptime(result['earliest_date'], '%d-%m-%Y').date()
                    latest_available = datetime.strptime(result['latest_date'], '%d-%m-%Y').date()
                    
                    # Default to 10 years ago or earliest available date, whichever is later
                    default_start = max(
                        earliest_available,
                        latest_available - timedelta(days=365*10)
                    )
                    
                    rolling_start_date = st.date_input(
                        "🎯 Analysis Start Date",
                        value=default_start,
                        min_value=earliest_available,
                        max_value=latest_available - timedelta(days=365*2),  # At least 2 years before end
                        help="Start date for rolling analysis",
                        format="DD-MM-YYYY"
                    )
                
                # Rolling CAGR compute button
                compute_rolling = st.button("🔄 Compute Rolling CAGR Analysis", type="primary")
                
                # Check if parameters have changed
                current_params = {
                    'window_years': window_years,
                    'start_date': rolling_start_date.strftime('%d-%m-%Y'),
                    'index': selected_index_name
                }
                
                if st.session_state.rolling_cagr_params != current_params:
                    st.session_state.rolling_cagr_computed = False
                    st.session_state.rolling_cagr_result = None
                
                # Compute rolling CAGR if button clicked
                if compute_rolling:
                    with st.spinner(f"📊 Computing rolling CAGR analysis for {selected_index_name}..."):
                        # Calculate rolling CAGR
                        rolling_result = calculate_rolling_cagr(
                            selected_symbol,
                            window_years=window_years,
                            start_date=rolling_start_date.strftime('%d-%m-%Y'),
                            stride_days=30
                        )
                        
                        # Store result in session state
                        st.session_state.rolling_cagr_result = rolling_result
                        st.session_state.rolling_cagr_computed = True
                        st.session_state.rolling_cagr_params = current_params
                
                # Display rolling CAGR if available in session state
                if st.session_state.rolling_cagr_computed and st.session_state.rolling_cagr_result:
                    rolling_result = st.session_state.rolling_cagr_result
                    
                    # Check if calculation was successful
                    if "error" in rolling_result:
                        st.markdown(f"""
                        <div class="error-card">
                            <h4>❌ Error Computing Rolling CAGR</h4>
                            <p><strong>Error:</strong> {rolling_result['error']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    else:
                        # Success - display rolling CAGR results
                        st.markdown(f"""
                        <div class="success-card">
                            <h4>✅ Rolling CAGR Analysis Complete</h4>
                            <p><strong>Index:</strong> {selected_index_name}</p>
                            <p><strong>Window Size:</strong> {rolling_result['window_years']} years</p>
                            <p><strong>Analysis Period:</strong> {rolling_result['analysis_period']}</p>
                            <p><strong>Total Windows:</strong> {rolling_result['total_windows']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Display rolling CAGR statistics
                        st.subheader("📈 Rolling CAGR Statistics")
                        
                        stat_col1, stat_col2, stat_col3 = st.columns(3)
                        
                        with stat_col1:
                            st.metric(
                                label="📊 Average CAGR",
                                value=f"{rolling_result['avg_cagr']:+.2f}%",
                                delta=None
                            )
                        
                        with stat_col2:
                            st.metric(
                                label="📈 Standard Deviation",
                                value=f"{rolling_result['std_cagr']:.2f}%",
                                delta=None
                            )
                        
                        with stat_col3:
                            st.metric(
                                label="🔢 Number of Windows",
                                value=rolling_result['total_windows'],
                                delta=None
                            )
                        
                        # Display detailed windows table
                        st.subheader("📋 Rolling CAGR Window Details")
                        
                        # Create a nice DataFrame for display
                        windows_df = pd.DataFrame(rolling_result['windows'])
                        windows_df = windows_df.rename(columns={
                            'window': 'Window',
                            'start_date': 'Start Date',
                            'end_date': 'End Date',
                            'start_nav': 'Start NAV',
                            'end_nav': 'End NAV',
                            'actual_years': 'Actual Years',
                            'cagr': 'CAGR (%)'
                        })
                        
                        # Format the DataFrame for better display
                        windows_df['Start NAV'] = windows_df['Start NAV'].apply(lambda x: f"₹{x:,.2f}")
                        windows_df['End NAV'] = windows_df['End NAV'].apply(lambda x: f"₹{x:,.2f}")
                        windows_df['CAGR (%)'] = windows_df['CAGR (%)'].apply(lambda x: f"{x:+.2f}%" if x is not None else "N/A")
                        
                        # Display the table
                        st.dataframe(
                            windows_df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Download button for the data
                        csv = windows_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Rolling CAGR Data as CSV",
                            data=csv,
                            file_name=f"{selected_index_name}_rolling_cagr_{rolling_result['window_years']}y.csv",
                            mime="text/csv"
                        )
    
    with col2:
        st.subheader("ℹ️ Information")
        
        if available_indices:
            st.markdown(f"""
            **Data Source:** Yahoo Finance API
            **Data Range:** Complete historical data available for each index
            """)
            
            # Show list of available indices
            with st.expander("📋 All Available Indices"):
                for name, symbol in available_indices.items():
                    st.write(f"• **{name}** (`{symbol}`)")
            
            # Show unavailable indices
            if unavailable_indices:
                with st.expander("❌ Unavailable Indices"):
                    for name, symbol in unavailable_indices.items():
                        st.write(f"• **{name}** (`{symbol}`)")

if __name__ == "__main__":
    main() 