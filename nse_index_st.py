#!/usr/bin/env python3
"""
Beautiful Streamlit App for NSE Index Data
Dynamic index availability checking with elegant UI using NSE APIs
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, date
import requests
import json
import os
from typing import Dict, List, Tuple, Optional
import numpy as np
from natsort import natsorted

# Page configuration
st.set_page_config(
    page_title="📈 NSE Index Data Explorer",
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

# Headers for NSE API requests
NSE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def load_local_nse_indices() -> Dict[str, str]:
    """
    Load NSE indices from local JSON file
    Returns a dictionary with indexName as key and indexSymbol as value
    """
    local_file_path = "assets/nse-index-names.json"
    
    try:
        if os.path.exists(local_file_path):
            with open(local_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            indices = {}
            
            # Parse the response - each item is [indexSymbol, indexName]
            if 'stn' in data:
                for item in data['stn']:
                    if len(item) >= 2:
                        index_symbol = item[0]
                        index_name = item[1]
                        if "NIFTY" in index_name:
                            index_name = "NIFTY " + index_name.split("NIFTY", 1)[1].strip()
                        indices[index_name] = index_symbol
            
            return indices
        else:
            return {"error": f"Local file not found: {local_file_path}"}
            
    except Exception as e:
        return {
            "error": f"Error reading local NSE indices file: {str(e)}",
            "error_details": {
                "file_path": local_file_path,
                "exception_type": type(e).__name__,
                "exception_message": str(e)
            }
        }

@st.cache_data()
def fetch_nse_indices() -> Dict[str, str]:
    """
    Fetch all NSE indices from the NSE API with local JSON fallback
    Returns a dictionary with indexName as key and indexSymbol as value
    """
    api_error_details = None
    
    # First try the API
    try:
        response = requests.get('https://www.nseindia.com/api/index-names', headers=NSE_HEADERS, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            indices = {}
            
            # Parse the response - each item is [indexSymbol, indexName]
            if 'stn' in data:
                for item in data['stn']:
                    if len(item) >= 2:
                        index_symbol = item[0]
                        index_name = item[1]
                        if "NIFTY" in index_name:
                            index_name = "NIFTY " + index_name.split("NIFTY", 1)[1].strip()
                        indices[index_name] = index_symbol
            
            return indices
        else:
            # Capture API error details
            api_error_details = {
                "status_code": response.status_code,
                "reason": response.reason,
                "headers": dict(response.headers),
                "url": response.url,
            }
            
            # Try to get response text
            try:
                api_error_details["response_text"] = response.text[:500]  # First 500 chars
            except:
                api_error_details["response_text"] = "Could not read response text"
            
    except Exception as e:
        # Capture API exception details
        api_error_details = {
            "exception_type": type(e).__name__,
            "exception_message": str(e)
        }
    
    # API failed, try local fallback
    st.warning("⚠️ NSE List-Indices API unavailable, using local list...")
    local_result = load_local_nse_indices()
    
    if "error" not in local_result:
        # Successfully loaded from local file
        return local_result
    else:
        # Both API and local file failed
        return {
            "error": f"Both NSE API and local fallback failed",
            "error_details": {
                "api_error": api_error_details,
                "local_error": local_result.get("error_details", local_result.get("error"))
            }
        }

def fetch_nse_historical_data(index_symbol: str, max_years: int = 20) -> Dict:
    """
    Fetch historical data for an NSE index
    Tries from max_years down to 1 year until successful
    """
    last_error_details = None
    
    try:
        for years in range(max_years, 0, -1):
            url = f"https://www.nseindia.com/api/NextApi/apiClient/historicalGraph?functionName=getIndexChart&&index={index_symbol}&flag={years}Y"
            
            try:
                response = requests.get(url, headers=NSE_HEADERS, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'data' in data and 'grapthData' in data['data']:
                        # Parse the data
                        graph_data = data['data']['grapthData']
                        
                        if not graph_data:
                            continue
                            
                        # Convert to DataFrame
                        df_data = []
                        for item in graph_data:
                            if len(item) >= 2:
                                timestamp = item[0]
                                value = item[1]
                                
                                # Convert timestamp to date
                                dt = datetime.fromtimestamp(timestamp / 1000)
                                df_data.append({
                                    'Date': dt.strftime('%d-%m-%Y'),
                                    'Close': float(value),
                                    'Timestamp': timestamp
                                })
                        
                        if df_data:
                            df = pd.DataFrame(df_data)
                            df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
                            df = df.sort_values('Date')
                            
                            # Calculate additional metrics
                            first_close = df['Close'].iloc[0]
                            last_close = df['Close'].iloc[-1]
                            earliest_date = df['Date'].min().strftime('%d-%m-%Y')
                            latest_date = df['Date'].max().strftime('%d-%m-%Y')
                            
                            # Calculate date difference
                            date_diff = (df['Date'].max() - df['Date'].min()).days
                            years_diff = round(date_diff / 365.25, 2)
                            
                            # Calculate CAGR
                            if first_close > 0 and years_diff > 0:
                                cagr = ((last_close / first_close) ** (1 / years_diff) - 1) * 100
                            else:
                                cagr = None
                            
                            return {
                                'index_symbol': index_symbol,
                                'index_name': data['data'].get('name', index_symbol),
                                'historical_data': df,
                                'earliest_date': earliest_date,
                                'latest_date': latest_date,
                                'first_close': first_close,
                                'last_close': last_close,
                                'total_data_points': len(df),
                                'days_diff': date_diff,
                                'years_diff': years_diff,
                                'cagr': cagr,
                                'absolute_change': last_close - first_close,
                                'percentage_change': ((last_close - first_close) / first_close) * 100 if first_close > 0 else 0,
                                'years_fetched': years
                            }
                
            except Exception as e:
                # Capture error details for the last attempt
                last_error_details = {
                    "years_attempted": years,
                    "url": url,
                    "status_code": getattr(response, 'status_code', 'N/A'),
                    "reason": getattr(response, 'reason', 'N/A'),
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                }
                
                # Try to get response text if response exists
                if 'response' in locals():
                    try:
                        last_error_details["response_text"] = response.text[:500]
                    except:
                        last_error_details["response_text"] = "Could not read response text"
                
                continue
        
        return {
            "error": f"Failed to fetch historical data for {index_symbol} after trying all year ranges (1-{max_years})",
            "error_details": last_error_details
        }
        
    except Exception as e:
        return {
            "error": f"Error fetching historical data: {str(e)}",
            "error_details": {
                "exception_type": type(e).__name__,
                "exception_message": str(e)
            }
        }

def calculate_nse_cagr(start_value: float, end_value: float, years: float) -> Optional[float]:
    """Calculate CAGR between two values"""
    if start_value <= 0 or end_value <= 0 or years <= 0:
        return None
    
    try:
        cagr = ((end_value / start_value) ** (1 / years) - 1) * 100
        return cagr
    except:
        return None

def calculate_nse_rolling_cagr(index_symbol: str, window_years: int = 5, start_date: str = None, stride_days: int = 21) -> Dict:
    """
    Calculate rolling CAGR for an NSE index using historical data
    
    Args:
        index_symbol: NSE index symbol
        window_years: Number of years for each rolling window
        start_date: Start date for analysis (format: DD-MM-YYYY)
        stride_days: Number of days to move forward for each window (default is 21 days, without weekends)
    """
    try:
        # Fetch historical data
        historical_result = fetch_nse_historical_data(index_symbol, max_years=20)
        
        if "error" in historical_result:
            return {"error": historical_result["error"]}
        
        df = historical_result['historical_data']
        
        if df.empty:
            return {"error": "No historical data available"}
        
        # Filter data based on start_date if provided
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%d-%m-%Y')
            df = df[df['Date'] >= start_date_obj]
            
            if df.empty:
                return {"error": "No data available from the specified start date"}
            
            # Reset index to ensure continuous indexing
            df = df.reset_index(drop=True)
        
        # Calculate rolling CAGR
        windows = []
        window_days = int(window_years * 365.25)
        
        # Check if we have enough data
        if len(df) < window_days // 30:  # Rough estimate of minimum required data points
            return {"error": f"Insufficient data for {window_years}-year rolling analysis. Need at least {window_days // 30} data points."}
        
        # Start from the earliest date + window_days
        start_idx = 0
        
        while start_idx < len(df):
            # Find the end date for this window
            window_start_date = df.iloc[start_idx]['Date']
            window_end_date = window_start_date + timedelta(days=window_days)
            
            # Find the closest end date in the data
            end_candidates = df[df['Date'] >= window_end_date]
            
            if len(end_candidates) > 0:
                # Get the first valid end date index
                end_idx = end_candidates.index[0]
                
                start_value = df.iloc[start_idx]['Close']
                end_value = df.iloc[end_idx]['Close']
                
                actual_start_date = df.iloc[start_idx]['Date']
                actual_end_date = df.iloc[end_idx]['Date']
                actual_years = (actual_end_date - actual_start_date).days / 365.25
                
                cagr = calculate_nse_cagr(start_value, end_value, actual_years)
                
                windows.append({
                    'window': len(windows) + 1,
                    'start_date': actual_start_date.strftime('%d-%m-%Y'),
                    'end_date': actual_end_date.strftime('%d-%m-%Y'),
                    'start_nav': start_value,
                    'end_nav': end_value,
                    'actual_years': round(actual_years, 2),
                    'cagr': round(cagr, 2) if cagr is not None else None
                })
                
                # Move to next window
                start_idx += stride_days
            else:
                # No more valid end dates found, break the loop
                break
        
        if not windows:
            return {"error": "Not enough data for rolling CAGR calculation"}
        
        # Calculate statistics
        valid_cagrs = [w['cagr'] for w in windows if w['cagr'] is not None]
        
        if not valid_cagrs:
            return {"error": "No valid CAGR calculations possible"}
        
        avg_cagr = np.mean(valid_cagrs)
        std_cagr = np.std(valid_cagrs)
        
        return {
            'index_symbol': index_symbol,
            'index_name': historical_result['index_name'],
            'window_years': window_years,
            'start_date': start_date,
            'analysis_period': f"{windows[0]['start_date']} to {windows[-1]['end_date']}",
            'total_windows': len(windows),
            'avg_cagr': round(avg_cagr, 2),
            'std_cagr': round(std_cagr, 2),
            'min_cagr': round(min(valid_cagrs), 2),
            'max_cagr': round(max(valid_cagrs), 2),
            'windows': windows
        }
        
    except Exception as e:
        return {"error": f"Error calculating rolling CAGR: {str(e)}"}

@st.cache_data()
def get_all_nse_indices():
    """
    Get all NSE indices - all indices are assumed to be available
    """
    return fetch_nse_indices()

def main():
    # Initialize ALL session state variables at the beginning
    if 'nse_historical_data_fetched' not in st.session_state:
        st.session_state.nse_historical_data_fetched = False
    if 'nse_current_index' not in st.session_state:
        st.session_state.nse_current_index = None
    if 'nse_historical_result' not in st.session_state:
        st.session_state.nse_historical_result = None
    if 'nse_rolling_cagr_computed' not in st.session_state:
        st.session_state.nse_rolling_cagr_computed = False
    if 'nse_rolling_cagr_result' not in st.session_state:
        st.session_state.nse_rolling_cagr_result = None
    if 'nse_rolling_cagr_params' not in st.session_state:
        st.session_state.nse_rolling_cagr_params = {}
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📈 NSE Index Data Explorer</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar for controls
    with st.sidebar:
        # Load all NSE indices
        with st.spinner("🔍 Loading NSE indices..."):
            all_indices = get_all_nse_indices()
        
        # Index selection
        st.subheader("📋 Select NSE Index")
        if "error" not in all_indices and all_indices:
            # Set default to "NIFTY 50" if available, otherwise use index 0
            index_list = natsorted(list(all_indices.keys()))
            try:
                default_index = index_list.index("NIFTY 50")
            except ValueError:
                default_index = 0
            
            selected_index_name = st.selectbox(
                "Choose an NSE index:",
                options=index_list,
                index=default_index,
                help="All NSE indices are available"
            )
            selected_symbol = all_indices[selected_index_name]
        else:
            if "error" in all_indices:
                st.markdown(f"""
                <div class="error-card">
                    <h4>❌ Error Loading NSE Indices</h4>
                    <p><strong>Error:</strong> {all_indices['error']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Display detailed error information if available
                if "error_details" in all_indices:
                    with st.expander("🔍 Detailed Error Information"):
                        error_details = all_indices["error_details"]
                        
                        if "status_code" in error_details:
                            st.write(f"**HTTP Status Code:** {error_details['status_code']}")
                            st.write(f"**Reason:** {error_details['reason']}")
                            st.write(f"**URL:** {error_details['url']}")
                            
                            if "response_text" in error_details:
                                st.write(f"**Response Text:**")
                                st.code(error_details['response_text'])
                            
                            if "headers" in error_details:
                                st.write(f"**Response Headers:**")
                                st.json(error_details['headers'])
                        
                        elif "exception_type" in error_details:
                            st.write(f"**Exception Type:** {error_details['exception_type']}")
                            st.write(f"**Exception Message:** {error_details['exception_message']}")
                        
                        else:
                            st.json(error_details)
            else:
                st.error("No NSE indices found. Please try refreshing.")
            return
        
        # Info about automatic date range
        st.subheader("📅 Data Range")
        st.info("📊 **Automatic Range**: All available historical data from NSE (up to 20 years) will be fetched.")
        
        # Submit button
        fetch_data = st.button("🚀 Fetch Complete NSE Historical Data & Calculate CAGR", type="primary")

        st.markdown("---")
        st.subheader("📊 NSE Index Info")
        
        st.markdown(f"""
        <div class="info-card">
            <p><strong>Total Indices:</strong> {len(all_indices)} indices</p>
            <p><strong>Data Source:</strong> NSE India Official API</p>
            <p><strong>Availability:</strong> All indices are available</p>
        </div>
        """, unsafe_allow_html=True)

        st.header("🎛️ Controls")
        
        # Refresh indices button
        if st.button("🔄 Refresh NSE Index List", type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
    
    # Main content area
    # Check if index has changed and reset session state if needed
    if st.session_state.nse_current_index != selected_index_name:
        st.session_state.nse_historical_data_fetched = False
        st.session_state.nse_current_index = selected_index_name
        st.session_state.nse_historical_result = None
        st.session_state.nse_rolling_cagr_computed = False
        st.session_state.nse_rolling_cagr_result = None
        st.session_state.nse_rolling_cagr_params = {}
    
    # Fetch data if button clicked
    if fetch_data and all_indices:
        with st.spinner(f"📊 Fetching complete NSE historical data for {selected_index_name}..."):
            # Fetch all historical data
            result = fetch_nse_historical_data(selected_symbol, max_years=20)
            
            # Store result in session state
            st.session_state.nse_historical_result = result
            st.session_state.nse_historical_data_fetched = True
    
    # Display historical data if available in session state
    if st.session_state.nse_historical_data_fetched and st.session_state.nse_historical_result:
        result = st.session_state.nse_historical_result
        
        # Check if fetch was successful
        if "error" in result:
            st.markdown(f"""
            <div class="error-card">
                <h4>❌ Error Fetching NSE Historical Data</h4>
                <p><strong>Index:</strong> {selected_index_name}</p>
                <p><strong>Error:</strong> {result['error']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Display detailed error information if available
            if "error_details" in result:
                with st.expander("🔍 Detailed Error Information"):
                    error_details = result["error_details"]
                    
                    if "years_attempted" in error_details:
                        st.write(f"**Years Attempted:** {error_details['years_attempted']}")
                        st.write(f"**URL:** {error_details['url']}")
                        st.write(f"**HTTP Status Code:** {error_details['status_code']}")
                        st.write(f"**Reason:** {error_details['reason']}")
                        
                        if "response_text" in error_details:
                            st.write(f"**Response Text:**")
                            st.code(error_details['response_text'])
                    
                    if "exception_type" in error_details:
                        st.write(f"**Exception Type:** {error_details['exception_type']}")
                        st.write(f"**Exception Message:** {error_details['exception_message']}")
                    
                    st.write(f"**Full Error Details:**")
                    st.json(error_details)
        
        else:
            # Success - display the data beautifully
            st.markdown(f"""
            <div class="success-card">
                <h4>✅ Complete NSE Historical Data Retrieved Successfully</h4>
                <p><strong>Index:</strong> {selected_index_name} ({selected_symbol})</p>
                <p><strong>Period:</strong> {result['earliest_date']} to {result['latest_date']}</p>
                <p><strong>Duration:</strong> {result['days_diff']} days ({result['years_diff']} years)</p>
                <p><strong>Data Points:</strong> {result['total_data_points']} trading days</p>
                <p><strong>Data Source:</strong> NSE India (fetched {result['years_fetched']} years)</p>
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
            with st.expander("📋 NSE Historical Data Summary"):
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
                    latest_available - timedelta(days=int(365.25*10))
                )
                
                rolling_start_date = st.date_input(
                    "🎯 Analysis Start Date",
                    value=default_start,
                    min_value=earliest_available,
                    max_value=latest_available - timedelta(days=int(365.25*2)),  # At least 2 years before end
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
            
            if st.session_state.nse_rolling_cagr_params != current_params:
                st.session_state.nse_rolling_cagr_computed = False
                st.session_state.nse_rolling_cagr_result = None
            
            # Compute rolling CAGR if button clicked
            if compute_rolling:
                with st.spinner(f"📊 Computing rolling CAGR analysis for {selected_index_name}..."):
                    # Calculate rolling CAGR
                    rolling_result = calculate_nse_rolling_cagr(
                        selected_symbol,
                        window_years=window_years,
                        start_date=rolling_start_date.strftime('%d-%m-%Y'),
                        stride_days=21
                    )
                    
                    # Store result in session state
                    st.session_state.nse_rolling_cagr_result = rolling_result
                    st.session_state.nse_rolling_cagr_computed = True
                    st.session_state.nse_rolling_cagr_params = current_params
            
            # Display rolling CAGR if available in session state
            if st.session_state.nse_rolling_cagr_computed and st.session_state.nse_rolling_cagr_result:
                rolling_result = st.session_state.nse_rolling_cagr_result
                
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
                    
                    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                    
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
                            label="📉 Min CAGR",
                            value=f"{rolling_result['min_cagr']:+.2f}%",
                            delta=None
                        )
                    
                    with stat_col4:
                        st.metric(
                            label="📈 Max CAGR",
                            value=f"{rolling_result['max_cagr']:+.2f}%",
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
                        file_name=f"NSE_{selected_index_name}_rolling_cagr_{rolling_result['window_years']}y.csv",
                        mime="text/csv"
                    )

if __name__ == "__main__":
    main() 