#!/usr/bin/env python3
"""
Script to fetch NIFTY index data using Yahoo Finance API
Updated to support all major NIFTY indices
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys
import time

def calculate_cagr(start_value, end_value, start_date, end_date):
    """Calculate Compound Annual Growth Rate (CAGR)"""
    
    # Convert string dates to datetime objects if needed and ensure timezone-naive
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%d-%m-%Y')
    else:
        # If it's already a datetime object, make sure it's timezone-naive
        start_date = start_date.replace(tzinfo=None) if start_date.tzinfo is not None else start_date
    
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%d-%m-%Y')
    else:
        # If it's already a datetime object, make sure it's timezone-naive
        end_date = end_date.replace(tzinfo=None) if end_date.tzinfo is not None else end_date
    
    # Calculate the number of years
    years = (end_date - start_date).days / 365.25
    
    if years <= 0 or start_value <= 0:
        return None
    
    # CAGR formula: (Ending Value / Beginning Value)^(1/number of years) - 1
    cagr = (end_value / start_value) ** (1 / years) - 1
    
    return cagr * 100  # Return as percentage

def calculate_rolling_cagr(nifty_symbol, window_years=5, start_date=None, stride_days=30):
    """
    Calculate rolling CAGR for a given index with specified window and stride
    
    Args:
        nifty_symbol (str): Yahoo Finance symbol for the index
        window_years (int): Number of years for each rolling window
        start_date (str): Start date for rolling analysis in 'DD-MM-YYYY' format
        stride_days (int): Number of days to move the window forward
    
    Returns:
        dict: Contains rolling CAGR analysis results
    """
    
    try:
        # Create ticker object and fetch all historical data
        ticker = yf.Ticker(nifty_symbol)
        hist_data = ticker.history(period="max")
        
        if hist_data.empty:
            return {
                "error": "No historical data available for this index",
                "symbol": nifty_symbol
            }
        
        # Convert start_date to datetime if provided, otherwise use earliest available
        if start_date:
            start_dt = datetime.strptime(start_date, '%d-%m-%Y')
            # Find the closest available date in historical data
            available_dates = hist_data.index
            closest_start = min(available_dates, key=lambda x: abs(x.replace(tzinfo=None) - start_dt))
            start_dt = closest_start
        else:
            start_dt = hist_data.index.min()
        
        # End date is the latest available date
        end_dt = hist_data.index.max()
        
        # Calculate window size in days
        window_days = window_years * 365.25
        
        # Generate rolling windows
        windows = []
        current_start = start_dt
        window_num = 1
        
        while True:
            # Calculate window end date
            window_end = current_start + timedelta(days=window_days)
            
            # Check if we have enough data for the full window period
            # Stop if the remaining time to end_dt is less than the full window
            remaining_days = (end_dt - current_start).days
            if remaining_days < window_days * 0.98:  # Allow 2% tolerance for weekends/holidays
                break
            
            # If window end exceeds available data, use the last available date
            if window_end > end_dt:
                window_end = end_dt
            
            # Double check - ensure we have at least 98% of the requested window period
            actual_days = (window_end - current_start).days
            if actual_days < window_days * 0.98:  # Less than 98% of requested window
                break
            
            # Find closest available dates in historical data
            start_prices = hist_data[hist_data.index <= current_start]
            end_prices = hist_data[hist_data.index <= window_end]
            
            if len(start_prices) == 0 or len(end_prices) == 0:
                current_start += timedelta(days=stride_days)
                continue
            
            # Get the actual start and end dates with available data
            actual_start_date = start_prices.index[-1]
            actual_end_date = end_prices.index[-1]
            
            # Get closing prices
            start_price = float(start_prices.iloc[-1]['Close'])
            end_price = float(end_prices.iloc[-1]['Close'])
            
            # Calculate actual years
            actual_years = (actual_end_date - actual_start_date).days / 365.25
            
            # Final check - ensure actual period is close to requested window
            if actual_years < window_years * 0.9:  # Less than 90% of requested window in years
                break
            
            # Calculate CAGR for this window
            if actual_years > 0 and start_price > 0:
                cagr = calculate_cagr(start_price, end_price, actual_start_date, actual_end_date)
                
                windows.append({
                    'window': window_num,
                    'start_date': actual_start_date.strftime('%d-%m-%Y'),
                    'end_date': actual_end_date.strftime('%d-%m-%Y'),
                    'start_nav': round(start_price, 2),
                    'end_nav': round(end_price, 2),
                    'actual_years': round(actual_years, 2),
                    'cagr': round(cagr, 2) if cagr is not None else None
                })
                
                window_num += 1
            
            # Move to next window
            current_start += timedelta(days=stride_days)
            
            # Stop if we've reached close to the end (no point in continuing)
            if current_start >= end_dt - timedelta(days=window_days * 0.9):
                break
        
        # Calculate statistics
        if windows:
            valid_cagrs = [w['cagr'] for w in windows if w['cagr'] is not None]
            
            if valid_cagrs:
                avg_cagr = sum(valid_cagrs) / len(valid_cagrs)
                std_cagr = (sum((x - avg_cagr) ** 2 for x in valid_cagrs) / len(valid_cagrs)) ** 0.5
                
                return {
                    "symbol": nifty_symbol,
                    "window_years": window_years,
                    "start_date": start_date,
                    "stride_days": stride_days,
                    "total_windows": len(windows),
                    "avg_cagr": round(avg_cagr, 2),
                    "std_cagr": round(std_cagr, 2),
                    "windows": windows,
                    "analysis_period": f"{windows[0]['start_date']} to {windows[-1]['end_date']}"
                }
            else:
                return {
                    "error": "No valid CAGR calculations possible",
                    "symbol": nifty_symbol
                }
        else:
            return {
                "error": "No rolling windows could be calculated with the given parameters",
                "symbol": nifty_symbol
            }
        
    except Exception as e:
        return {
            "error": str(e),
            "symbol": nifty_symbol
        }

def fetch_all_historical_data(nifty_symbol, max_period="max"):
    """
    Fetch all available historical data for a given index
    
    Args:
        nifty_symbol (str): Yahoo Finance symbol for the index
        max_period (str): Period to fetch data for ('max' for all available data)
    
    Returns:
        dict: Contains all historical data, earliest date, latest date, and CAGR
    """
    
    try:
        # Create ticker object
        ticker = yf.Ticker(nifty_symbol)
        
        # Fetch all available historical data
        hist_data = ticker.history(period=max_period)
        
        if hist_data.empty:
            return {
                "error": "No historical data available for this index",
                "symbol": nifty_symbol
            }
        
        # Get the earliest and latest dates
        earliest_date = hist_data.index.min()
        latest_date = hist_data.index.max()
        
        # Get first and last closing prices
        first_close = float(hist_data.iloc[0]['Close'])
        last_close = float(hist_data.iloc[-1]['Close'])
        
        # Calculate CAGR
        cagr = calculate_cagr(first_close, last_close, earliest_date, latest_date)
        
        # Calculate absolute and percentage change
        absolute_change = last_close - first_close
        percentage_change = (absolute_change / first_close) * 100
        
        # Calculate days between dates
        days_diff = (latest_date - earliest_date).days
        years_diff = days_diff / 365.25
        
        result = {
            "symbol": nifty_symbol,
            "earliest_date": earliest_date.strftime('%d-%m-%Y'),
            "latest_date": latest_date.strftime('%d-%m-%Y'),
            "first_close": round(first_close, 2),
            "last_close": round(last_close, 2),
            "absolute_change": round(absolute_change, 2),
            "percentage_change": round(percentage_change, 2),
            "cagr": round(cagr, 2) if cagr is not None else None,
            "days_diff": days_diff,
            "years_diff": round(years_diff, 2),
            "total_data_points": len(hist_data),
            "historical_data": hist_data  # Include the full dataset for charting
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "symbol": nifty_symbol
        }

def fetch_index_data(target_date, nifty_symbol):
    """
    Fetch index closing price and OHLC data for a specific date
    
    Args:
        target_date (str): Date in format 'DD-MM-YYYY'
        nifty_symbol (str): Yahoo Finance symbol for the index
    
    Returns:
        dict: Contains date, closing price, and other OHLC data
    """
    
    try:
        # Create ticker object
        ticker = yf.Ticker(nifty_symbol)
        
        # Convert target date to datetime
        target_dt = datetime.strptime(target_date, '%d-%m-%Y')
        
        # Fetch data for a range around the target date
        # Yahoo Finance needs a date range, so we'll get data for a week around target date
        start_date = target_dt - timedelta(days=7)
        end_date = target_dt + timedelta(days=7)
        
        # Fetch historical data
        hist_data = ticker.history(start=start_date, end=end_date)
        
        if hist_data.empty:
            return {
                "error": "No data available for the specified date range",
                "target_date": target_date,
                "symbol": nifty_symbol
            }
        
        # Try to find exact date or closest available date
        target_date_str = target_date
        
        if target_date_str in hist_data.index.strftime('%d-%m-%Y'):
            # Exact date found
            row = hist_data[hist_data.index.strftime('%d-%m-%Y') == target_date_str].iloc[0]
            exact_match = True
        else:
            # Find closest available date - handle timezone issues by normalizing
            target_date_only = target_dt.date()
            
            # Calculate date differences safely
            date_diffs = []
            for idx in hist_data.index:
                idx_date = idx.date() if hasattr(idx, 'date') else idx.to_pydatetime().date()
                diff = abs((idx_date - target_date_only).days)
                date_diffs.append(diff)
            
            hist_data['date_diff'] = date_diffs
            closest_idx = hist_data['date_diff'].idxmin()
            row = hist_data.loc[closest_idx]
            exact_match = False
            target_date_str = closest_idx.strftime('%d-%m-%Y')
        
        result = {
            "symbol": nifty_symbol,
            "requested_date": target_date,
            "actual_date": target_date_str,
            "exact_match": exact_match,
            "open": round(row['Open'], 2),
            "high": round(row['High'], 2),
            "low": round(row['Low'], 2),
            "close": round(row['Close'], 2),
            "volume": int(row['Volume']) if 'Volume' in row and pd.notna(row['Volume']) else 0
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "target_date": target_date,
            "symbol": nifty_symbol
        }

def get_available_indices():
    """
    Get comprehensive list of all major NIFTY indices available via Yahoo Finance
    
    Based on NSE Indices Limited official indices list
    Total: 80+ indices across broad market, sectoral, and thematic categories
    """
    
    # Comprehensive list of all major NIFTY indices with Yahoo Finance symbols
    indices = {
        # BROAD MARKET INDICES (15 indices)
        "NIFTY 50": "^NSEI",
        "NIFTY NEXT 50": "^NSMIDCP", 
        "NIFTY 100": "^CNX100",
        "NIFTY 200": "^CNX200",
        "NIFTY 500": "^CRSLDX",
        "NIFTY LARGEMIDCAP 250": "NIFTY_LARGEMID250.NS",
        "NIFTY MIDCAP 50": "^NSEMDCP50",
        "NIFTY MIDCAP 100": "^CNX100",
        "NIFTY MIDCAP 150": "NIFTYMIDCAP150.NS",
        "NIFTY MIDCAP SELECT": "NIFTY_MID_SELECT.NS",
        "NIFTY SMALLCAP 50": "NIFTYSMLCAP50.NS",
        "NIFTY SMALLCAP 100": "^CNXSC",
        "NIFTY SMALLCAP 250": "NIFTYSMLCAP250.NS",
        "NIFTY MICROCAP 250": "NIFTY_MICROCAP250.NS",
        "NIFTY TOTAL MARKET": "NIFTY_TOTAL_MKT.NS",
        
        # SECTORAL INDICES (21 indices)
        "NIFTY AUTO": "^CNXAUTO",
        "NIFTY BANK": "^NSEBANK",
        "NIFTY FINANCIAL SERVICES": "NIFTY_FIN_SERVICE.NS",
        "NIFTY FMCG": "^CNXFMCG",
        "NIFTY IT": "^CNXIT",
        "NIFTY MEDIA": "^CNXMEDIA",
        "NIFTY METAL": "^CNXMETAL",
        "NIFTY PHARMA": "^CNXPHARMA",
        "NIFTY PSU BANK": "^CNXPSUBANK",
        "NIFTY REALTY": "^CNXREALTY",
        "NIFTY PRIVATE BANK": "NIFTYPVTBANK.NS",
        "NIFTY HEALTHCARE": "NIFTY_HEALTHCARE.NS",
        "NIFTY CONSUMER DURABLES": "NIFTY_CONSR_DURBL.NS",
        "NIFTY OIL & GAS": "NIFTY_OIL_AND_GAS.NS",
        "NIFTY COMMODITIES": "^CNXCMDT",
        "NIFTY CONSUMPTION": "^CNXCONSUM",
        "NIFTY CPSE": "CPSE.NS",
        "NIFTY ENERGY": "^CNXENERGY",
        "NIFTY INFRASTRUCTURE": "^CNXINFRA",
        "NIFTY PSE": "^CNXPSE",
        "NIFTY SERVICES SECTOR": "^CNXSERVICE",
        
        # THEMATIC/STRATEGY INDICES (20+ indices)
        "NIFTY DIVIDEND OPPORTUNITIES 50": "NETFDIVOPP.NS",
        "NIFTY GROWTH SECTORS 15": "HDFCGROWTH.NS",
        "NIFTY100 QUALITY 30": "EQ30.NS",
        "NIFTY50 VALUE 20": "NV20.NS",
        # "NIFTY100 ALPHA 30": "NIFTY100ALPHA30.NS",
        "NIFTY200 QUALITY 30": "NIFTY200QUALITY30.NS",
        "NIFTY ALPHA 50": "NIFTYALPHA50.NS",
        "NIFTY HIGH BETA 50": "NIFTYHIGHBETA50.NS",
        "NIFTY LOW VOLATILITY 50": "NIFTYLOWVOL50.NS",
        "NIFTY QUALITY LOW-VOLATILITY 30": "NIFTYQUALITYLOWVOL30.NS",
        "NIFTY ALPHA QUALITY LOW-VOLATILITY 30": "NIFTYALPHAQUALITYLOWVOL30.NS",
        "NIFTY ALPHA QUALITY VALUE LOW-VOLATILITY 30": "NIFTYALPHAQUALITYVALUELOWVOL30.NS",
        "NIFTY200 MOMENTUM 30": "NIFTY200MOMENTUM30.NS",
        "NIFTY MIDCAP LIQUID 15": "NIFTYMIDCAPLIQUID15.NS",
        "NIFTY100 ESG SECTOR LEADERS": "NIFTY100ESGSECTORLEADERS.NS",
        "NIFTY100 ENHANCED ESG": "NIFTY100ENHANCEDESG.NS",
        "NIFTY500 MULTICAP 50:25:25": "NIFTY500MULTICAP502525.NS",
        "NIFTY SMALLCAP 50": "^CNXSC",
        "NIFTY MICROCAP 250": "NIFTYMICROCAP250.NS",
        
        # ADDITIONAL IMPORTANT INDICES
        "BSE SENSEX": "^BSESN",
        "BSE 100": "BSE-100.BO",
        "BSE 200": "BSE-200.BO",
        "BSE 500": "BSE-500.BO",
        "BSE MIDCAP": "BSE-MIDCAP.BO",
        "BSE SMALLCAP": "BSE-SMLCAP.BO",
        
        # BOND INDICES (Some available)
        "NIFTY 10 YR BENCHMARK G-SEC": "NIFTY10YRBENCHMARKGSEC.NS",
        "NIFTY 4-8 YR G-SEC INDEX": "NIFTY48YRGSECINDEX.NS",
        "NIFTY 8-13 YR G-SEC INDEX": "NIFTY813YRGSECINDEX.NS",
        "NIFTY 15 YR AND ABOVE G-SEC INDEX": "NIFTY15YRABOVEGSECINDEX.NS",
        
        # VOLATILITY INDEX
        "INDIA VIX": "^INDIAVIX"
    }
    
    print(f"COMPREHENSIVE LIST OF ALL MAJOR NIFTY INDICES")
    print(f"Total Indices Available: {len(indices)}")
    print("=" * 80)
    
    # Group indices by category
    broad_market = [k for k in indices.keys() if any(x in k for x in ["NIFTY 50", "NIFTY NEXT", "NIFTY 100", "NIFTY 200", "NIFTY 500", "MIDCAP", "SMALLCAP", "MICROCAP", "TOTAL MARKET", "LARGEMIDCAP"])]
    sectoral = [k for k in indices.keys() if any(x in k for x in ["AUTO", "BANK", "FINANCIAL", "FMCG", "IT", "MEDIA", "METAL", "PHARMA", "REALTY", "HEALTHCARE", "CONSUMER", "OIL", "COMMODIT", "CONSUMPTION", "CPSE", "ENERGY", "INFRASTRUCTURE", "PSE", "SERVICE"])]
    thematic = [k for k in indices.keys() if any(x in k for x in ["DIVIDEND", "GROWTH", "QUALITY", "VALUE", "ALPHA", "BETA", "VOLATILITY", "MOMENTUM", "LIQUID", "ESG", "MULTICAP"])]
    others = [k for k in indices.keys() if k not in broad_market + sectoral + thematic]
    
    print(f"\n📊 BROAD MARKET INDICES ({len(broad_market)} indices):")
    print("-" * 60)
    for name in sorted(broad_market):
        print(f"{name:<40} : {indices[name]}")
    
    print(f"\n🏭 SECTORAL INDICES ({len(sectoral)} indices):")
    print("-" * 60)
    for name in sorted(sectoral):
        print(f"{name:<40} : {indices[name]}")
    
    print(f"\n🎯 THEMATIC/STRATEGY INDICES ({len(thematic)} indices):")
    print("-" * 60)
    for name in sorted(thematic):
        print(f"{name:<40} : {indices[name]}")
    
    if others:
        print(f"\n📈 OTHER INDICES ({len(others)} indices):")
        print("-" * 60)
        for name in sorted(others):
            print(f"{name:<40} : {indices[name]}")
    
    return indices

def test_all_indices_for_date(target_date, max_indices=10):
    """
    Test fetching data for multiple indices for a given date
    
    Args:
        target_date (str): Date in format 'DD-MM-YYYY'
        max_indices (int): Maximum number of indices to test (to avoid overwhelming output)
    """
    
    indices = get_available_indices()
    
    print(f"\n\n🔍 TESTING DATA AVAILABILITY FOR DATE: {target_date}")
    print("=" * 80)
    print(f"Testing first {max_indices} indices (to avoid overwhelming output):")
    print("-" * 60)
    
    successful = 0
    failed = 0
    results = []
    
    # Test a subset of indices
    test_indices = list(indices.items())[:max_indices]
    
    for i, (name, symbol) in enumerate(test_indices, 1):
        print(f"\n{i:2d}. Testing {name} ({symbol})...")
        
        result = fetch_index_data(target_date, symbol)
        
        if "error" in result:
            print(f"    ❌ Failed: {result['error']}")
            failed += 1
        else:
            print(f"    ✅ Success: Close = ₹{result['close']:,}")
            successful += 1
            results.append({
                'name': name,
                'symbol': symbol,
                'close': result['close'],
                'date': result['actual_date']
            })
        
        # Small delay to be respectful to the API
        time.sleep(0.5)
    
    print(f"\n📊 SUMMARY:")
    print(f"   Successful: {successful}/{len(test_indices)}")
    print(f"   Failed: {failed}/{len(test_indices)}")
    
    if results:
        print(f"\n✅ SUCCESSFUL RESULTS:")
        print("-" * 60)
        for r in results:
            print(f"   {r['name']:<30} : ₹{r['close']:>10,} (Date: {r['date']})")
    
    return results

def main():
    print("COMPREHENSIVE NIFTY INDICES DATA FETCHER")
    print("=" * 80)
    
    # Show all available indices
    indices = get_available_indices()
    
    # Test data for the requested date
    target_date = "30-06-2025"
    
    print(f"\n\n🎯 MAIN TASK: Fetching data for {target_date}")
    print("Note: Since this is a future date, results may be unexpected.")
    print("=" * 80)
    
    # Test a subset of indices to see which ones work
    results = test_all_indices_for_date(target_date, max_indices=15)
    
    # Show usage example for the generalized function
    print(f"\n\n💡 USAGE EXAMPLES:")
    print("=" * 80)
    print("# Fetch NIFTY50 data:")
    print('result = fetch_index_data("30-06-2025", "^NSEI")')
    print()
    print("# Fetch NIFTY BANK data:")
    print('result = fetch_index_data("30-06-2025", "^NSEBANK")')
    print()
    print("# Fetch any index data:")
    print('result = fetch_index_data("30-06-2025", "NIFTY500MULTICAP502525.NS")')

if __name__ == "__main__":
    main()