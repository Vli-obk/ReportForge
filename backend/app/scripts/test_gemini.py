"""
Example script to test Gemini integration locally
Usage: python scripts/test_gemini.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.gemini_service import GeminiService

__test__ = False


def test_gemini_connection():
    """Test if Gemini service is running"""
    print("=" * 60)
    print("Testing Gemini Connection")
    print("=" * 60)
    
    gemini = GeminiService(api_key="")
    
    if gemini.is_service_available():
        print(f"✓ Gemini service is reachable at {gemini.base_url}")
    else:
        print("✗ Gemini service is NOT reachable")
        print("  Set GEMINI_API_URL and GEMINI_API_KEY in .env")
        return False
    
    return True


def test_text_extraction():
    """Test structured data extraction from sample text"""
    print("\n" + "=" * 60)
    print("Testing Text Extraction with Gemini")
    print("=" * 60)
    
    # Sample business data text (simulating PDF extraction)
    sample_text = """
    Business Report Data:
    
    Manufacturing Business - NAICS Code 325991
    Sales: $2,500,000
    Percent Change: +3.5%
    Median CV: 8.2%
    
    Retail Trade - NAICS Code 442110
    Sales: $1,800,000
    Percent Change: -1.2%
    Median CV: 15.3%
    
    Professional Services - NAICS Code 541110
    Sales: $3,200,000
    Percent Change: +7.8%
    Median CV: 5.9%
    """
    
    print(f"\nInput text:\n{sample_text}")
    
    gemini = GeminiService(api_key="")
    
    try:
        print("\nCalling Gemini to extract structured data...")
        structured_data = gemini.extract_structured_data(sample_text)
        
        print(f"\n✓ Successfully extracted {len(structured_data)} records:\n")
        for i, record in enumerate(structured_data, 1):
            print(f"Record {i}:")
            for key, value in record.items():
                print(f"  {key}: {value}")
            print()
        
        return structured_data
        
    except Exception as e:
        print(f"✗ Error during extraction: {e}")
        return None


def test_csv_export(structured_data):
    """Test CSV export functionality"""
    print("=" * 60)
    print("Testing CSV Export")
    print("=" * 60)
    
    if not structured_data:
        print("No data to export")
        return
    
    gemini = GeminiService(api_key="")
    output_path = "test_output.csv"
    
    try:
        csv_path = gemini.save_to_csv(structured_data, output_path)
        print(f"✓ CSV saved successfully to: {csv_path}")
        
        # Read and display
        import pandas as pd
        df = pd.read_csv(csv_path)
        print(f"\nDataFrame shape: {df.shape}")
        print(f"\nFirst few rows:\n{df.head()}")
        
    except Exception as e:
        print(f"✗ Error during CSV export: {e}")


def test_complete_pipeline():

    print("\n" + "=" * 60)
    print("Testing Complete Pipeline")
    print("=" * 60)
    
    sample_text = """
    Industry Report:
    
    Information Technology Services
    NAICS 541512
    Total Sales: $5,600,000
    YoY Change: 12.3%
    Coefficient of Variation: 3.8%
    
    Advertising Agencies
    NAICS 541810
    Total Sales: $890,000
    YoY Change: -2.1%
    Coefficient of Variation: 22.4%
    """
    
    gemini = GeminiService(api_key="")
    output_path = "complete_pipeline_test.csv"
    
    try:
        print(f"\nProcessing text through complete pipeline...")
        result_path = gemini.process_pdf_text_to_csv(sample_text, output_path)
        print(f"✓ Complete pipeline successful!")
        print(f"  CSV saved to: {result_path}")
        
        # Display results
        import pandas as pd
        df = pd.read_csv(result_path)
        print(f"\nExtracted Data ({df.shape[0]} rows):\n")
        print(df.to_string(index=False))
        
    except Exception as e:
        print(f"✗ Pipeline failed: {e}")


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  Gemini Integration Test Suite".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    
    # Test 1: Connection
    if not test_gemini_connection():
        print("\n✗ Cannot continue without Gemini running")
        sys.exit(1)
    
    # Test 2: Extraction
    structured_data = test_text_extraction()
    
    if structured_data:
        # Test 3: CSV Export
        test_csv_export(structured_data)
        
        # Test 4: Complete Pipeline
        test_complete_pipeline()
        
        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        print("=" * 60)
    else:
        print("\n✗ Extraction test failed, skipping remaining tests")
        sys.exit(1)


if __name__ == "__main__":
    main()
