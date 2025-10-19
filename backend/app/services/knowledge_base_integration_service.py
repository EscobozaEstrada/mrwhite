"""
Knowledge Base Integration Service

This service demonstrates and tests end-to-end knowledge base integration
across all chat endpoints and provides utilities for monitoring and validation.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from flask import current_app

from app.services.ai_service import AIService
from app.services.unified_chat_storage_service import get_unified_chat_storage
from app.services.context7_semantic_service import get_context7_service
from app.services.common_knowledge_service import CommonKnowledgeService
from app.services.care_archive_service import CareArchiveService
from app.models.care_record import KnowledgeBase
from app.models.conversation import Conversation
from app.models.message import Message
from app import db

logger = logging.getLogger(__name__)

class KnowledgeBaseIntegrationService:
    """Service for testing and validating complete knowledge base integration"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.storage_service = get_unified_chat_storage()
        self.context7_service = get_context7_service()
        self.common_knowledge_service = CommonKnowledgeService()
        self.care_archive_service = CareArchiveService()
    
    def test_end_to_end_integration(self, user_id: int) -> Dict[str, Any]:
        """
        Test complete end-to-end knowledge base integration
        
        This tests:
        1. Message storage in both PostgreSQL and Pinecone
        2. Knowledge retrieval from all sources
        3. Context7 semantic analysis
        4. Common knowledge base integration
        5. Response generation with full context
        """
        test_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "tests": {
                "storage_test": {"success": False, "details": {}},
                "retrieval_test": {"success": False, "details": {}},
                "semantic_analysis_test": {"success": False, "details": {}},
                "common_knowledge_test": {"success": False, "details": {}},
                "integration_test": {"success": False, "details": {}},
            },
            "overall_success": False,
            "recommendations": []
        }
        
        try:
            current_app.logger.info(f"🧪 Starting end-to-end integration test for user {user_id}")
            
            # Test 1: Storage Integration
            test_results["tests"]["storage_test"] = self._test_message_storage(user_id)
            
            # Test 2: Knowledge Retrieval
            test_results["tests"]["retrieval_test"] = self._test_knowledge_retrieval(user_id)
            
            # Test 3: Semantic Analysis
            test_results["tests"]["semantic_analysis_test"] = self._test_semantic_analysis()
            
            # Test 4: Common Knowledge Integration
            test_results["tests"]["common_knowledge_test"] = self._test_common_knowledge_integration()
            
            # Test 5: Full Integration Test
            test_results["tests"]["integration_test"] = self._test_full_integration(user_id)
            
            # Calculate overall success
            all_tests_passed = all(
                test["success"] for test in test_results["tests"].values()
            )
            test_results["overall_success"] = all_tests_passed
            
            # Generate recommendations
            test_results["recommendations"] = self._generate_recommendations(test_results["tests"])
            
            current_app.logger.info(f"✅ Integration test completed: {all_tests_passed}")
            return test_results
            
        except Exception as e:
            current_app.logger.error(f"❌ Integration test failed: {str(e)}")
            test_results["error"] = str(e)
            return test_results
    
    def _test_message_storage(self, user_id: int) -> Dict[str, Any]:
        """Test message storage in both PostgreSQL and Pinecone"""
        try:
            # Create a test conversation
            test_conversation = Conversation(
                user_id=user_id,
                title="Integration Test Conversation"
            )
            db.session.add(test_conversation)
            db.session.commit()
            
            test_message = "This is a test message for integration testing."
            test_response = "This is a test AI response."
            
            # Test unified storage
            success, storage_info = self.storage_service.store_message_complete(
                user_id=user_id,
                conversation_id=test_conversation.id,
                user_message=test_message,
                ai_response=test_response,
                context_info={"test": True, "intent": "testing"}
            )
            
            # Verify database storage
            stored_messages = Message.query.filter_by(conversation_id=test_conversation.id).all()
            db_storage_success = len(stored_messages) == 2
            
            # Test vector retrieval
            chat_docs = self.ai_service.search_chat_history(test_message, user_id, top_k=1)
            vector_storage_success = len(chat_docs) > 0
            
            return {
                "success": success and db_storage_success,
                "details": {
                    "unified_storage": success,
                    "storage_info": storage_info,
                    "database_messages": len(stored_messages),
                    "vector_retrieval": vector_storage_success,
                    "test_conversation_id": test_conversation.id
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "details": {"error": str(e)}
            }
    
    def _test_knowledge_retrieval(self, user_id: int) -> Dict[str, Any]:
        """Test comprehensive knowledge retrieval from all sources"""
        try:
            test_query = "vaccination schedule for my dog"
            
            # Test comprehensive search
            knowledge_sources = self.ai_service.comprehensive_knowledge_search(
                query=test_query,
                user_id=user_id,
                include_common_knowledge=True
            )
            
            sources_found = {
                source: len(docs) for source, docs in knowledge_sources.items()
            }
            
            total_sources = len([s for s in sources_found.values() if s > 0])
            
            return {
                "success": total_sources > 0,
                "details": {
                    "sources_found": sources_found,
                    "total_active_sources": total_sources,
                    "query_tested": test_query
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "details": {"error": str(e)}
            }
    
    def _test_semantic_analysis(self) -> Dict[str, Any]:
        """Test Context7 semantic analysis"""
        try:
            test_messages = [
                "My dog is vomiting and won't eat - is this an emergency?",
                "I love my golden retriever so much, he brings me joy every day",
                "How do I teach my puppy to sit and stay?",
                "Show me my dog's vaccination records from last month"
            ]
            
            analysis_results = []
            for message in test_messages:
                analysis = self.context7_service.analyze_content_semantics(message)
                analysis_results.append({
                    "message": message,
                    "content_type": analysis.content_type.value,
                    "relevance_score": analysis.relevance_score,
                    "urgency_level": analysis.urgency_level,
                    "key_concepts": analysis.key_concepts
                })
            
            # Verify different content types were detected
            content_types = set(r["content_type"] for r in analysis_results)
            
            return {
                "success": len(content_types) >= 3,  # Should detect at least 3 different types
                "details": {
                    "analyses_performed": len(analysis_results),
                    "content_types_detected": list(content_types),
                    "sample_analysis": analysis_results[0] if analysis_results else None
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "details": {"error": str(e)}
            }
    
    def _test_common_knowledge_integration(self) -> Dict[str, Any]:
        """Test common knowledge base integration"""
        try:
            if not self.common_knowledge_service.is_service_available():
                return {
                    "success": False,
                    "details": {"error": "Common knowledge service not available"}
                }
            
            test_query = "dog training techniques"
            success, results = self.common_knowledge_service.search_common_knowledge(
                query=test_query,
                top_k=3
            )
            
            return {
                "success": success and len(results) > 0,
                "details": {
                    "search_successful": success,
                    "results_found": len(results),
                    "sample_result": results[0] if results else None,
                    "query_tested": test_query
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "details": {"error": str(e)}
            }
    
    def _test_full_integration(self, user_id: int) -> Dict[str, Any]:
        """Test complete integration with a realistic chat scenario"""
        try:
            # Simulate a realistic chat interaction
            test_scenarios = [
                {
                    "message": "My dog has been limping after our walk yesterday. Should I be worried?",
                    "expected_type": "health_query",
                    "should_find_context": True
                },
                {
                    "message": "What's the best way to train a puppy to walk on a leash?",
                    "expected_type": "training_advice", 
                    "should_include_book_knowledge": True
                }
            ]
            
            integration_results = []
            
            for scenario in test_scenarios:
                # Perform semantic analysis
                analysis = self.context7_service.analyze_content_semantics(scenario["message"])
                
                # Search all knowledge sources
                knowledge_sources = self.ai_service.comprehensive_knowledge_search(
                    query=scenario["message"],
                    user_id=user_id,
                    include_common_knowledge=True
                )
                
                # Check if common knowledge was found for training questions
                common_knowledge_found = len(knowledge_sources.get("common_knowledge", [])) > 0
                
                integration_results.append({
                    "scenario": scenario["message"],
                    "content_type_detected": analysis.content_type.value,
                    "content_type_expected": scenario["expected_type"],
                    "content_type_match": analysis.content_type.value == scenario["expected_type"],
                    "knowledge_sources_found": len([s for s in knowledge_sources.values() if s]),
                    "common_knowledge_found": common_knowledge_found,
                    "relevance_score": analysis.relevance_score
                })
            
            # Calculate success metrics
            type_accuracy = sum(1 for r in integration_results if r["content_type_match"]) / len(integration_results)
            knowledge_integration = all(r["knowledge_sources_found"] > 0 for r in integration_results)
            
            return {
                "success": type_accuracy >= 0.5 and knowledge_integration,
                "details": {
                    "scenarios_tested": len(test_scenarios),
                    "content_type_accuracy": type_accuracy,
                    "knowledge_integration_working": knowledge_integration,
                    "detailed_results": integration_results
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "details": {"error": str(e)}
            }
    
    def _generate_recommendations(self, test_results: Dict[str, Dict]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if not test_results["storage_test"]["success"]:
            recommendations.append("Fix message storage integration - check database and vector storage")
        
        if not test_results["retrieval_test"]["success"]:
            recommendations.append("Improve knowledge retrieval - ensure all sources are properly indexed")
        
        if not test_results["semantic_analysis_test"]["success"]:
            recommendations.append("Enhance Context7 semantic analysis - check pattern matching accuracy")
        
        if not test_results["common_knowledge_test"]["success"]:
            recommendations.append("Setup common knowledge base properly - verify Pinecone integration")
        
        if not test_results["integration_test"]["success"]:
            recommendations.append("Fix end-to-end integration - check service coordination and routing")
        
        if not recommendations:
            recommendations.append("All tests passed! Knowledge base integration is working correctly.")
        
        return recommendations
    
    def get_knowledge_base_stats(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive knowledge base statistics for a user"""
        try:
            # Database statistics
            total_conversations = Conversation.query.filter_by(user_id=user_id).count()
            total_messages = db.session.query(Message).join(Conversation)\
                .filter(Conversation.user_id == user_id).count()
            
            # Knowledge base record
            kb_record = KnowledgeBase.query.filter_by(user_id=user_id).first()
            
            # Care archive stats
            care_results = CareArchiveService.search_user_archive(user_id, "health", limit=1)
            
            return {
                "user_id": user_id,
                "database_stats": {
                    "total_conversations": total_conversations,
                    "total_messages": total_messages
                },
                "knowledge_base": {
                    "exists": kb_record is not None,
                    "vector_count": kb_record.vector_count if kb_record else 0,
                    "last_updated": kb_record.last_updated.isoformat() if kb_record and kb_record.last_updated else None,
                    "namespace": kb_record.pinecone_namespace if kb_record else None,
                    "metadata": kb_record.meta_data if kb_record else {}
                },
                "care_archive": {
                    "documents_available": len(care_results.get("documents", [])),
                    "care_records_available": len(care_results.get("care_records", [])),
                    "common_knowledge_available": care_results.get("common_knowledge_available", False)
                },
                "common_knowledge_service": {
                    "available": self.common_knowledge_service.is_service_available()
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting knowledge base stats: {str(e)}")
            return {"error": str(e), "user_id": user_id}
    
    def diagnose_knowledge_gaps(self, user_id: int, query: str) -> Dict[str, Any]:
        """Diagnose knowledge gaps for a specific query"""
        try:
            current_app.logger.info(f"🔍 Diagnosing knowledge gaps for query: {query}")
            
            # Perform semantic analysis
            analysis = self.context7_service.analyze_content_semantics(query)
            
            # Search all knowledge sources
            knowledge_sources = self.ai_service.comprehensive_knowledge_search(
                query=query,
                user_id=user_id,
                include_common_knowledge=True
            )
            
            # Identify gaps
            gaps = []
            recommendations = []
            
            if not knowledge_sources.get("user_documents"):
                gaps.append("No relevant user documents found")
                recommendations.append("Upload relevant documents or PDFs for better context")
            
            if not knowledge_sources.get("chat_history"):
                gaps.append("No relevant chat history found")
                recommendations.append("This appears to be a new topic - responses will be more general")
            
            if not knowledge_sources.get("care_records"):
                gaps.append("No relevant care records found")
                recommendations.append("Add care records for personalized health advice")
            
            if not knowledge_sources.get("common_knowledge"):
                gaps.append("No relevant book knowledge found")
                recommendations.append("Query might benefit from different keywords")
            
            return {
                "query": query,
                "semantic_analysis": {
                    "content_type": analysis.content_type.value,
                    "relevance_score": analysis.relevance_score,
                    "urgency_level": analysis.urgency_level
                },
                "knowledge_sources": {
                    source: len(docs) for source, docs in knowledge_sources.items()
                },
                "identified_gaps": gaps,
                "recommendations": recommendations,
                "overall_completeness": len([s for s in knowledge_sources.values() if s]) / len(knowledge_sources)
            }
            
        except Exception as e:
            current_app.logger.error(f"Error diagnosing knowledge gaps: {str(e)}")
            return {"error": str(e), "query": query}


# Global service instance
_integration_service = None

def get_integration_service() -> KnowledgeBaseIntegrationService:
    """Get singleton instance of integration service"""
    global _integration_service
    if _integration_service is None:
        _integration_service = KnowledgeBaseIntegrationService()
    return _integration_service 