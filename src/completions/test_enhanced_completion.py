#!/usr/bin/env python3
"""
Enhanced Completion Performance Test

Tests the improved thinking chain completion system with detailed performance metrics.
"""

import argparse
import time
import asyncio
import requests
import json
from typing import Dict, List, Any

# Test prompts for different domains
TEST_PROMPTS = [
    {
        "prompt": "Explain machine learning algorithms and their practical applications",
        "category": "Technical",
        "expected_domains": ["computer science", "data science", "algorithms"]
    },
    {
        "prompt": "How do I improve team leadership skills in a remote work environment?", 
        "category": "Management",
        "expected_domains": ["leadership", "management", "communication"]
    },
    {
        "prompt": "What are the latest trends in sustainable energy and their economic impact?",
        "category": "Business/Tech",
        "expected_domains": ["energy", "sustainability", "economics"]
    },
    {
        "prompt": "How can I optimize database query performance for large datasets?",
        "category": "Technical",
        "expected_domains": ["database", "optimization", "performance"]
    },
    {
        "prompt": "What strategies work best for customer retention in SaaS businesses?",
        "category": "Business",
        "expected_domains": ["business", "customer success", "SaaS"]
    }
]

class EnhancedCompletionTester:
    """Test suite for enhanced completion system"""
    
    def __init__(self, base_url: str = "http://localhost:8000", user_id: str = None):
        self.base_url = base_url
        self.user_id = user_id or "test-user-enhanced"
        self.results = []
        
    def test_single_completion(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single completion request"""
        
        print(f"\n🔍 Testing: {prompt_data['category']} - {prompt_data['prompt'][:60]}...")
        
        # Prepare request
        request_data = {
            "prompt": prompt_data["prompt"],
            "temperature": 0.7,
            "max_tokens": 200,
            "user_id": self.user_id
        }
        
        # Time the request
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.base_url}/api/completions/",
                json=request_data,
                timeout=30
            )
            
            total_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract performance metrics
                api_processing_time = result.get("usage", {}).get("processing_time_ms", 0)
                completion_text = result["choices"][0]["text"]
                
                # Analyze response quality
                quality_metrics = self._analyze_response_quality(
                    prompt_data["prompt"], 
                    completion_text,
                    prompt_data["expected_domains"]
                )
                
                test_result = {
                    "category": prompt_data["category"],
                    "prompt": prompt_data["prompt"][:100] + "...",
                    "success": True,
                    "total_time_s": round(total_time, 2),
                    "api_processing_time_ms": api_processing_time,
                    "response_length": len(completion_text),
                    "token_usage": result.get("usage", {}),
                    "quality_score": quality_metrics["overall_score"],
                    "quality_details": quality_metrics,
                    "response_preview": completion_text[:200] + "..." if len(completion_text) > 200 else completion_text
                }
                
                print(f"✅ Success: {total_time:.2f}s total, {api_processing_time}ms processing")
                print(f"📊 Quality Score: {quality_metrics['overall_score']}/10")
                
                return test_result
                
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return {
                    "category": prompt_data["category"],
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "total_time_s": round(total_time, 2)
                }
                
        except Exception as e:
            total_time = time.time() - start_time
            print(f"❌ Exception: {str(e)}")
            return {
                "category": prompt_data["category"],
                "success": False,
                "error": str(e),
                "total_time_s": round(total_time, 2)
            }
    
    def _analyze_response_quality(self, prompt: str, response: str, expected_domains: List[str]) -> Dict[str, Any]:
        """Analyze response quality based on various metrics"""
        
        response_lower = response.lower()
        
        # Check domain relevance
        domain_matches = sum(1 for domain in expected_domains if domain.lower() in response_lower)
        domain_score = min(10, (domain_matches / len(expected_domains)) * 10)
        
        # Check response length appropriateness
        length_score = min(10, len(response.split()) / 20)  # Aim for substantial responses
        
        # Check for structured thinking indicators
        thinking_indicators = [
            "first", "second", "third", "initially", "then", "finally",
            "consider", "analysis", "approach", "strategy", "because",
            "therefore", "however", "specifically", "example", "such as"
        ]
        thinking_matches = sum(1 for indicator in thinking_indicators if indicator in response_lower)
        thinking_score = min(10, thinking_matches / 2)
        
        # Check for professional language
        professional_terms = [
            "implement", "optimize", "framework", "methodology", "best practices",
            "strategic", "effective", "efficient", "comprehensive", "systematic"
        ]
        professional_matches = sum(1 for term in professional_terms if term in response_lower)
        professional_score = min(10, professional_matches)
        
        # Overall score
        overall_score = round((domain_score + length_score + thinking_score + professional_score) / 4, 1)
        
        return {
            "overall_score": overall_score,
            "domain_relevance": round(domain_score, 1),
            "response_depth": round(length_score, 1),
            "structured_thinking": round(thinking_score, 1),
            "professional_language": round(professional_score, 1),
            "word_count": len(response.split())
        }
    
    def run_benchmark(self) -> Dict[str, Any]:
        """Run complete benchmark test"""
        
        print("🚀 Starting Enhanced Completion Benchmark")
        print(f"📡 API Endpoint: {self.base_url}/api/completions/")
        print(f"👤 User ID: {self.user_id}")
        print(f"📝 Test Prompts: {len(TEST_PROMPTS)}")
        
        # Test each prompt
        for i, prompt_data in enumerate(TEST_PROMPTS, 1):
            print(f"\n📋 Test {i}/{len(TEST_PROMPTS)}")
            result = self.test_single_completion(prompt_data)
            self.results.append(result)
            
            # Brief pause between tests
            time.sleep(1)
        
        # Calculate summary statistics
        summary = self._calculate_summary()
        
        print("\n" + "="*60)
        print("📊 ENHANCED COMPLETION BENCHMARK RESULTS")
        print("="*60)
        
        print(f"\n✅ Successful requests: {summary['successful_tests']}/{summary['total_tests']}")
        print(f"⏱️  Average response time: {summary['avg_response_time']:.2f}s")
        print(f"🔥 Fastest response: {summary['fastest_time']:.2f}s")
        print(f"🐌 Slowest response: {summary['slowest_time']:.2f}s")
        print(f"🎯 Average quality score: {summary['avg_quality_score']}/10")
        print(f"📏 Average response length: {summary['avg_response_length']} words")
        
        # Quality breakdown
        print(f"\n📈 Quality Metrics:")
        print(f"   Domain Relevance: {summary['avg_domain_relevance']}/10")
        print(f"   Response Depth: {summary['avg_response_depth']}/10")
        print(f"   Structured Thinking: {summary['avg_structured_thinking']}/10")
        print(f"   Professional Language: {summary['avg_professional_language']}/10")
        
        # Show best and worst performers
        if summary['successful_tests'] > 0:
            best_test = max([r for r in self.results if r.get('success')], 
                           key=lambda x: x.get('quality_score', 0))
            worst_test = min([r for r in self.results if r.get('success')], 
                            key=lambda x: x.get('quality_score', 0))
            
            print(f"\n🏆 Best Performance:")
            print(f"   Category: {best_test['category']}")
            print(f"   Quality: {best_test['quality_score']}/10")
            print(f"   Time: {best_test['total_time_s']}s")
            
            print(f"\n⚠️  Needs Improvement:")
            print(f"   Category: {worst_test['category']}")
            print(f"   Quality: {worst_test['quality_score']}/10")
            print(f"   Time: {worst_test['total_time_s']}s")
        
        return {
            "summary": summary,
            "detailed_results": self.results
        }
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics"""
        
        successful_results = [r for r in self.results if r.get('success', False)]
        
        if not successful_results:
            return {
                "total_tests": len(self.results),
                "successful_tests": 0,
                "avg_response_time": 0,
                "avg_quality_score": 0
            }
        
        times = [r['total_time_s'] for r in successful_results]
        quality_scores = [r.get('quality_score', 0) for r in successful_results]
        response_lengths = [r.get('quality_details', {}).get('word_count', 0) for r in successful_results]
        
        quality_details = [r.get('quality_details', {}) for r in successful_results]
        
        return {
            "total_tests": len(self.results),
            "successful_tests": len(successful_results),
            "avg_response_time": sum(times) / len(times),
            "fastest_time": min(times),
            "slowest_time": max(times),
            "avg_quality_score": round(sum(quality_scores) / len(quality_scores), 1),
            "avg_response_length": round(sum(response_lengths) / len(response_lengths)),
            "avg_domain_relevance": round(sum(d.get('domain_relevance', 0) for d in quality_details) / len(quality_details), 1),
            "avg_response_depth": round(sum(d.get('response_depth', 0) for d in quality_details) / len(quality_details), 1),
            "avg_structured_thinking": round(sum(d.get('structured_thinking', 0) for d in quality_details) / len(quality_details), 1),
            "avg_professional_language": round(sum(d.get('professional_language', 0) for d in quality_details) / len(quality_details), 1)
        }

def main():
    parser = argparse.ArgumentParser(description='Test enhanced completion system')
    parser.add_argument('--user-id', default='test-user-enhanced', help='User ID for testing')
    parser.add_argument('--url', default='http://localhost:8000', help='API base URL')
    parser.add_argument('--output', help='Save results to JSON file')
    parser.add_argument('--quick-test', action='store_true', help='Run a single quick test first')
    
    args = parser.parse_args()
    
    if args.quick_test:
        # Run a single quick test first
        print("🧪 Running Quick Test First...")
        tester = EnhancedCompletionTester(base_url=args.url, user_id=args.user_id)
        quick_prompt = {
            "prompt": "How can I improve my programming skills?",
            "category": "Quick Test",
            "expected_domains": ["programming", "learning", "development"]
        }
        result = tester.test_single_completion(quick_prompt)
        
        if result.get('success'):
            print("✅ Quick test passed! Running full benchmark...")
            print(f"📊 Quick test quality: {result.get('quality_score', 0)}/10")
            print(f"⏱️  Quick test time: {result.get('total_time_s', 0)}s")
        else:
            print("❌ Quick test failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            return
    
    # Run benchmark
    tester = EnhancedCompletionTester(base_url=args.url, user_id=args.user_id)
    results = tester.run_benchmark()
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {args.output}")

if __name__ == "__main__":
    main() 