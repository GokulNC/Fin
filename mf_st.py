import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import math
from typing import Dict, List, Optional

# Configure Streamlit page
st.set_page_config(
    page_title="Mutual Fund Analyzer", 
    page_icon="📈", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2e86de;
        margin-top: 2rem;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .metric-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .stMetric > label {
        font-size: 0.8rem !important;
    }
    .stMetric > div[data-testid="metric-value"] {
        font-size: 1rem !important;
    }
    .stMetric [data-testid="metric-value"] > div {
        font-size: 1rem !important;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .info-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #e8f5e8;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        border-left: 4px solid #4caf50;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_all_mutual_funds() -> List[Dict]:
    """Fetch all mutual funds from the API and cache the result."""
    try:
        with st.spinner("Fetching mutual fund list..."):
            response = requests.get("https://api.mfapi.in/mf", timeout=30)
            response.raise_for_status()
            return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching mutual fund list: {str(e)}")
        return []

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_mutual_fund_data(scheme_code: int) -> Optional[Dict]:
    """Fetch historical data for a specific mutual fund scheme."""
    try:
        with st.spinner(f"Fetching data for scheme {scheme_code}..."):
            response = requests.get(f"https://api.mfapi.in/mf/{scheme_code}", timeout=30)
            response.raise_for_status()
            return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data for scheme {scheme_code}: {str(e)}")
        return None

def calculate_cagr(start_value: float, end_value: float, years: float) -> float:
    """Calculate Compound Annual Growth Rate (CAGR)."""
    if start_value <= 0 or end_value <= 0 or years <= 0:
        return 0.0
    return ((end_value / start_value) ** (1/years) - 1) * 100

def calculate_years_since_nfo(start_date: str, end_date: str) -> float:
    """Calculate the number of years between two dates."""
    try:
        start = datetime.strptime(start_date, "%d-%m-%Y")
        end = datetime.strptime(end_date, "%d-%m-%Y")
        days_diff = (end - start).days
        return round(days_diff / 365.25, 1)  # Account for leap years
    except ValueError:
        return 0.0

def calculate_rolling_cagr(data: List[Dict], window_years: int) -> Dict:
    """Calculate rolling CAGR for a given time window."""
    try:
        # Convert data to DataFrame and sort by date
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
        df['nav'] = df['nav'].astype(float)
        df = df.sort_values('date').reset_index(drop=True)
        
        window_days = window_years * 365.25
        stride_days = 21  # Approximately 1 month, without weekends
        
        cagr_values = []
        window_details = []
        
        # Rolling window calculation
        for i in range(0, len(df), stride_days):
            start_idx = i
            
            # Find end index for the window
            start_date = df.iloc[start_idx]['date']
            target_end_date = start_date + pd.Timedelta(days=window_days)
            
            # Find the closest date to target end date
            end_idx = None
            for j in range(start_idx + 1, len(df)):
                if df.iloc[j]['date'] >= target_end_date:
                    end_idx = j
                    break
            
            if end_idx is None:
                break  # Not enough data for this window
            
            # Calculate CAGR for this window
            start_nav = df.iloc[start_idx]['nav']
            end_nav = df.iloc[end_idx]['nav']
            actual_start_date = df.iloc[start_idx]['date']
            actual_end_date = df.iloc[end_idx]['date']
            actual_days = (actual_end_date - actual_start_date).days
            actual_years = actual_days / 365.25
            
            if start_nav > 0 and end_nav > 0 and actual_years > 0:
                cagr = ((end_nav / start_nav) ** (1/actual_years) - 1) * 100
                cagr_values.append(cagr)
                
                # Store window details
                window_details.append({
                    "Window": len(window_details) + 1,
                    "Start Date": actual_start_date.strftime('%d-%m-%Y'),
                    "End Date": actual_end_date.strftime('%d-%m-%Y'),
                    "Start NAV": f"₹{start_nav:.4f}",
                    "End NAV": f"₹{end_nav:.4f}",
                    "Actual Years": round(actual_years, 2),
                    "CAGR (%)": round(cagr, 2)
                })
        
        if not cagr_values:
            return {"average_cagr": 0.0, "std_dev": 0.0, "num_windows": 0, "window_details": []}
        
        return {
            "average_cagr": round(sum(cagr_values) / len(cagr_values), 2),
            "std_dev": round(pd.Series(cagr_values).std(), 2),
            "num_windows": len(cagr_values),
            "cagr_values": cagr_values,
            "window_details": window_details
        }
    
    except Exception as e:
        st.error(f"Error calculating rolling CAGR: {str(e)}")
        return {"average_cagr": 0.0, "std_dev": 0.0, "num_windows": 0, "window_details": []}

def main():
    """Main application function."""
    
    # Header
    st.markdown('<div class="main-header">📈 Mutual Fund Analyzer</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar for controls
    with st.sidebar:
        st.markdown("### 🎛️ Controls")
        
        # Fetch all mutual funds
        mf_list = fetch_all_mutual_funds()
        
        if not mf_list:
            st.error("Failed to load mutual fund data. Please check your internet connection and try again.")
            return
        
        # Create sorted list of scheme names with codes for mapping
        scheme_options = {}
        for mf in mf_list:
            scheme_name = mf.get('schemeName', 'Unknown')
            scheme_code = mf.get('schemeCode')
            if scheme_name and scheme_code:
                scheme_options[scheme_name] = scheme_code
        
        # Sort scheme names alphabetically
        sorted_schemes = sorted(scheme_options.keys())
        
        st.success(f"✅ Loaded {len(sorted_schemes)} mutual fund schemes")
        
        # Dropdown for scheme selection
        selected_scheme = st.selectbox(
            "🔍 Select Mutual Fund Scheme:",
            options=sorted_schemes,
            help="Choose a mutual fund scheme to analyze"
        )
        
        # Fetch data button
        fetch_button = st.button("📊 Fetch Data", type="primary", use_container_width=True)
    
    # Initialize session state
    if 'scheme_data' not in st.session_state:
        st.session_state.scheme_data = None
    if 'selected_scheme_name' not in st.session_state:
        st.session_state.selected_scheme_name = None
    
    # Process data when button is clicked
    if fetch_button and selected_scheme:
        scheme_code = scheme_options[selected_scheme]
        
        # Fetch scheme data
        scheme_data = fetch_mutual_fund_data(scheme_code)
        
        if not scheme_data or scheme_data.get('status') != 'SUCCESS':
            st.error("Failed to fetch scheme data. Please try again.")
            return
        
        # Store in session state
        st.session_state.scheme_data = scheme_data
        st.session_state.selected_scheme_name = selected_scheme
    
    # Main content area - show welcome message if no data
    if not st.session_state.scheme_data:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown('<div class="info-box">👈 Select a mutual fund scheme from the sidebar and click "Fetch Data" to view detailed analysis.</div>', unsafe_allow_html=True)
        
        with col2:
            if len(sorted_schemes) > 0:
                st.metric("Total Schemes Available", len(sorted_schemes))
        return
    
    # Use data from session state
    scheme_data = st.session_state.scheme_data
    meta = scheme_data.get('meta', {})
    data = scheme_data.get('data', [])
    
    if not data:
        st.error("No historical data available for this scheme.")
        return

    # Display scheme information
    st.markdown('<div class="section-header">📋 Scheme Information</div>', unsafe_allow_html=True)
    
    # Create scheme info table
    scheme_info_data = {
        "Attribute": [
            "Scheme Name",
            "Scheme Code", 
            "Scheme Category",
            "Scheme Type",
            "Fund House",
            "ISIN Growth"
        ],
        "Details": [
            meta.get('scheme_name', 'N/A'),
            str(meta.get('scheme_code', 'N/A')),
            meta.get('scheme_category', 'N/A'),
            meta.get('scheme_type', 'N/A'),
            meta.get('fund_house', 'N/A'),
            meta.get('isin_growth', 'N/A')
        ]
    }
    
    scheme_df = pd.DataFrame(scheme_info_data)
    st.dataframe(
        scheme_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Attribute": st.column_config.TextColumn("Attribute", width="medium"),
            "Details": st.column_config.TextColumn("Details", width="large")
        }
    )
    
    # Performance Analysis
    st.markdown('<div class="section-header">📊 Performance Analysis</div>', unsafe_allow_html=True)
    
    # Get latest and first data points
    latest_data = data[0]  # First item is the latest
    first_data = data[-1]  # Last item is the oldest (NFO)
    
    latest_nav = float(latest_data['nav'])
    nfo_nav = float(first_data['nav'])
    latest_date = latest_data['date']
    nfo_date = first_data['date']
    
    # Calculate metrics
    years_since_nfo = calculate_years_since_nfo(nfo_date, latest_date)
    cagr = calculate_cagr(nfo_nav, latest_nav, years_since_nfo)
    
    # Display performance metrics
    perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
    
    with perf_col1:
        st.metric(
            f"Current NAV ({latest_date})", 
            f"₹{latest_nav:.4f}"
        )
    
    with perf_col2:
        st.metric(
            f"Initial NAV ({nfo_date})", 
            f"₹{nfo_nav:.4f}"
        )
    
    with perf_col3:
        st.metric(
            "Years Since Initial NAV", 
            f"{years_since_nfo} years",
            help="Time elapsed since Initial NAV"
        )
    
    with perf_col4:
        cagr_color = "normal" if cagr >= 0 else "inverse"
        st.metric(
            "CAGR", 
            f"{cagr:.2f}%",
            help="Compound Annual Growth Rate"
        )
    
    # Additional insights
    if cagr > 0:
        st.markdown(f'<div class="success-box">🎉 This fund has delivered a positive CAGR of {cagr:.2f}% over {years_since_nfo} years since NFO.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="info-box">📉 This fund has a negative CAGR of {cagr:.2f}% over {years_since_nfo} years since NFO.</div>', unsafe_allow_html=True)
    
    # Rolling CAGR Analysis
    st.markdown('<div class="section-header">📊 Rolling CAGR Analysis</div>', unsafe_allow_html=True)
    
    rolling_col1, rolling_col2 = st.columns([2, 1])
    
    with rolling_col1:
        st.markdown("**Analyze CAGR performance across different time windows:**")
        window_years = st.slider(
            "Select Time Window (Years)",
            min_value=2,
            max_value=10,
            value=5,
            step=1,
            help="Choose the rolling window size in years for CAGR analysis"
        )
    
    with rolling_col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Add some spacing
        calculate_rolling = st.button("🔄 Calculate Rolling CAGR", type="secondary", use_container_width=True)
    
    # Process rolling CAGR calculation
    if calculate_rolling:
        with st.spinner(f"Calculating {window_years}-year rolling CAGR..."):
            rolling_results = calculate_rolling_cagr(data, window_years)
            
            if rolling_results["num_windows"] > 0:
                # Display results
                st.markdown("### 📈 Rolling CAGR Results")
                
                result_col1, result_col2, result_col3 = st.columns(3)
                
                with result_col1:
                    st.metric(
                        f"Average CAGR ({window_years}Y)",
                        f"{rolling_results['average_cagr']:.2f}%"
                    )
                
                with result_col2:
                    st.metric(
                        "Standard Deviation",
                        f"{rolling_results['std_dev']:.2f}%"
                    )
                
                with result_col3:
                    st.metric(
                        "Windows Analyzed",
                        rolling_results['num_windows']
                    )
                
                # Additional insights for rolling CAGR
                avg_cagr = rolling_results['average_cagr']
                std_dev = rolling_results['std_dev']
                
                if std_dev < 5:
                    volatility_desc = "low volatility"
                    volatility_color = "success-box"
                elif std_dev < 10:
                    volatility_desc = "moderate volatility"
                    volatility_color = "info-box"
                else:
                    volatility_desc = "high volatility"
                    volatility_color = "info-box"
                
                st.markdown(f'<div class="{volatility_color}">📊 Over {window_years}-year rolling windows, this fund shows an average CAGR of {avg_cagr:.2f}% with {volatility_desc} (±{std_dev:.2f}%).</div>', unsafe_allow_html=True)
                
                # Show CAGR distribution info
                cagr_values = rolling_results['cagr_values']
                min_cagr = min(cagr_values)
                max_cagr = max(cagr_values)
                
                st.markdown(f"**CAGR Range:** {min_cagr:.2f}% (minimum) to {max_cagr:.2f}% (maximum)")
                
                # Display detailed window analysis table
                if rolling_results.get('window_details'):
                    st.markdown("### 📋 Detailed Window Analysis")
                    
                    window_df = pd.DataFrame(rolling_results['window_details'])
                    
                    # Display the table with custom column configuration
                    st.dataframe(
                        window_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Window": st.column_config.NumberColumn("Window #", width="small"),
                            "Start Date": st.column_config.TextColumn("Start Date", width="medium"),
                            "End Date": st.column_config.TextColumn("End Date", width="medium"),
                            "Start NAV": st.column_config.TextColumn("Start NAV", width="medium"),
                            "End NAV": st.column_config.TextColumn("End NAV", width="medium"),
                            "Actual Years": st.column_config.NumberColumn("Years", width="small", format="%.2f"),
                            "CAGR (%)": st.column_config.NumberColumn("CAGR (%)", width="medium", format="%.2f")
                        },
                        height=min(400, len(window_df) * 35 + 50)  # Dynamic height based on number of rows
                    )
                    
                    st.info(f"📊 This table shows all {len(window_df)} rolling {window_years}-year windows analyzed for CAGR calculation.")
                
            else:
                st.warning(f"Not enough data to calculate {window_years}-year rolling CAGR. Try a smaller time window.")
    
    else:
        st.info(f"💡 Select a time window and click 'Calculate Rolling CAGR' to analyze {window_years}-year performance patterns.")

if __name__ == "__main__":
    main() 