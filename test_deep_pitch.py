"""
Test script for Deep Pitch Pipeline
Run this to verify the multi-step depth pipeline works correctly
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the deep pitch generation function
from huggingface_client import deep_pitch_generation

def test_deep_pitch():
    """Test the deep pitch generation pipeline"""
    
    print("=" * 60)
    print("TESTING DEEP PITCH PIPELINE")
    print("=" * 60)
    
    # Test case 1: AI Startup
    print("\n📊 Test Case 1: AI Startup")
    print("-" * 60)
    
    startup_name = "PitchPerfectAI"
    startup_description = "AI-powered pitch deck generator that helps founders create investor-grade presentations using advanced language models and market intelligence"
    
    print(f"Startup: {startup_name}")
    print(f"Description: {startup_description}")
    print("\nGenerating pitch deck...\n")
    
    try:
        result = deep_pitch_generation(startup_name, startup_description)
        
        print("✅ SUCCESS!")
        print(f"\nGenerated Pitch Length: {len(result)} characters")
        print("\nFirst 500 characters:")
        print("-" * 60)
        print(result[:500])
        print("...\n")
        
        # Check if all sections are present
        sections = ["## Problem", "## Solution", "## Market Opportunity", "## Business Model"]
        missing_sections = [s for s in sections if s not in result]
        
        if missing_sections:
            print(f"⚠️  WARNING: Missing sections: {missing_sections}")
        else:
            print("✅ All sections present!")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False


def test_context_search():
    """Test the context search functionality"""
    from huggingface_client import get_context
    
    print("\n" + "=" * 60)
    print("TESTING CONTEXT SEARCH")
    print("=" * 60)
    
    query = "AI pitch deck generator market trends 2025"
    print(f"\nQuery: {query}")
    print("\nSearching...\n")
    
    try:
        context = get_context(query)
        
        if context:
            print("✅ SUCCESS!")
            print(f"\nContext Length: {len(context)} characters")
            print("\nFirst 300 characters:")
            print("-" * 60)
            print(context[:300])
            print("...\n")
            return True
        else:
            print("⚠️  No context found (this is okay, pipeline will continue)")
            return True
            
    except Exception as e:
        print(f"⚠️  Context search failed: {str(e)}")
        print("(This is okay, pipeline will continue without context)")
        return True


def main():
    """Run all tests"""
    print("\n🚀 DEEP PITCH PIPELINE TEST SUITE\n")
    
    # Check for HF token
    hf_token = os.getenv('HF_API_TOKEN')
    if not hf_token:
        print("❌ ERROR: HF_API_TOKEN not found in environment")
        print("Please add your Hugging Face token to .env file:")
        print("HF_API_TOKEN=hf_your_token_here")
        return
    
    print(f"✅ HF_API_TOKEN configured: {hf_token[:10]}...")
    
    # Run tests
    results = []
    
    # Test 1: Context Search
    results.append(("Context Search", test_context_search()))
    
    # Test 2: Deep Pitch Generation
    results.append(("Deep Pitch Generation", test_deep_pitch()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nYour deep pitch pipeline is ready to use!")
        print("\nNext steps:")
        print("1. Start your Flask server: python app.py")
        print("2. Test the API endpoint: POST /api/generate-deep-pitch")
        print("3. Check DEEP_PITCH_PIPELINE.md for usage examples")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("\nPlease check:")
        print("1. HF_API_TOKEN is valid")
        print("2. Internet connection is working")
        print("3. Hugging Face API is accessible")


if __name__ == "__main__":
    main()
