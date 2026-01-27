#!/usr/bin/env python3
"""
Master deployment script for the comprehensive Horizon Europe RAG system.
This script orchestrates the entire process from document acquisition to system testing.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("deployment.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class ComprehensiveSystemDeployer:
    """Deploy the comprehensive Horizon Europe RAG system."""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.scripts_dir = self.base_dir / "scripts"
        self.processed_dir = self.base_dir / "processed_docs" / "horizon_europe"
        self.test_reports_dir = self.base_dir / "test_reports"

        # Create necessary directories
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.test_reports_dir.mkdir(exist_ok=True)

        logger.info("🚀 Comprehensive Horizon Europe RAG System Deployment")
        logger.info("=" * 60)

    async def run_command(self, command: str, description: str, cwd: str = None) -> bool:
        """Run a shell command with proper logging."""
        logger.info(f"🔄 {description}...")
        logger.info(f"   Command: {command}")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd or str(self.base_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"✅ {description} completed successfully")
                if stdout:
                    logger.debug(f"   Output: {stdout.decode()[:500]}...")
                return True
            else:
                logger.error(f"❌ {description} failed with return code {process.returncode}")
                if stderr:
                    logger.error(f"   Error: {stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"❌ {description} failed with exception: {e}")
            return False

    async def download_all_documents(self) -> bool:
        """Download comprehensive Horizon Europe documents."""
        logger.info("📥 Step 1: Downloading comprehensive Horizon Europe documents...")

        script_path = self.scripts_dir / "download_all_horizon_calls.py"
        if not script_path.exists():
            logger.error(f"❌ Download script not found: {script_path}")
            return False

        success = await self.run_command(
            f"python {script_path}", "Downloading Horizon Europe documents"
        )

        if success:
            # Check if documents were downloaded
            download_dir = self.base_dir / "downloaded_docs" / "horizon_europe"
            if download_dir.exists() and any(download_dir.iterdir()):
                logger.info(f"✅ Documents downloaded to: {download_dir}")
                return True
            else:
                logger.error("❌ No documents found after download")
                return False
        return False

    async def process_documents(self) -> bool:
        """Process downloaded documents for ingestion."""
        logger.info("🔧 Step 2: Processing documents for vector database ingestion...")

        script_path = self.scripts_dir / "process_comprehensive_docs.py"
        if not script_path.exists():
            logger.error(f"❌ Processing script not found: {script_path}")
            return False

        success = await self.run_command(f"python {script_path}", "Processing documents")

        if success:
            # Check if processing was successful
            processed_file = self.processed_dir / "processed_documents.json"
            if processed_file.exists():
                logger.info(f"✅ Documents processed successfully: {processed_file}")
                return True
            else:
                logger.error("❌ No processed documents found")
                return False
        return False

    async def ingest_documents(self) -> bool:
        """Ingest processed documents into vector database."""
        logger.info("📊 Step 3: Ingesting documents into vector database...")

        script_path = self.scripts_dir / "ingest_comprehensive_docs.py"
        if not script_path.exists():
            logger.error(f"❌ Ingestion script not found: {script_path}")
            return False

        success = await self.run_command(
            f"python {script_path}", "Ingesting documents into vector database"
        )

        if success:
            # Check if ingestion was successful
            stats_file = self.processed_dir / "post_ingestion_stats.json"
            if stats_file.exists():
                with open(stats_file) as f:
                    stats = json.load(f)
                logger.info(
                    f"✅ Documents ingested successfully. Stats: {json.dumps(stats, indent=2)}"
                )
                return True
            else:
                logger.error("❌ No ingestion stats found")
                return False
        return False

    async def test_system(self) -> bool:
        """Test the enhanced RAG system with comprehensive queries."""
        logger.info("🧪 Step 4: Testing the enhanced Call-Specific RAG system...")

        script_path = self.scripts_dir / "test_call_specific_rag.py"
        if not script_path.exists():
            logger.error(f"❌ Test script not found: {script_path}")
            return False

        success = await self.run_command(
            f"python {script_path}", "Testing Call-Specific RAG system"
        )

        if success:
            # Check if test report was generated
            test_reports = list(self.test_reports_dir.glob("call_specific_rag_test_*.json"))
            if test_reports:
                latest_report = max(test_reports, key=lambda x: x.stat().st_mtime)
                logger.info(f"✅ System testing completed. Report: {latest_report}")

                # Load and analyze test results
                with open(latest_report) as f:
                    report = json.load(f)

                success_rate = report["summary"]["overall_success_rate"]
                logger.info(f"📊 Test Results: {success_rate:.1%} overall success rate")

                return success_rate > 0.7  # Consider successful if >70%
            else:
                logger.error("❌ No test reports found")
                return False
        return False

    async def verify_database_content(self) -> bool:
        """Verify that the database contains comprehensive call documentation."""
        logger.info("🔍 Step 5: Verifying database content...")

        try:
            from app.services.embedding_service import EmbeddingService
            from app.services.supabase_client import SupabaseVectorStore
            from app.services.vector_search_service import VectorSearchService

            supabase = SupabaseVectorStore()
            embedder = EmbeddingService(cache_client=supabase)
            vector_search = VectorSearchService(supabase, embedder)

            # Test searches for different call types
            test_queries = [
                "HORIZON-CL4-2024-DATA-01-01",
                "health cluster calls",
                "ERC grants eligibility",
                "Horizon Europe Work Programme",
            ]

            results = {}
            for query in test_queries:
                search_results = vector_search.search(
                    query=query, search_type="semantic", num_results=5, similarity_threshold=0.6
                )
                results[query] = {
                    "found": len(search_results) > 0,
                    "count": len(search_results),
                    "top_score": search_results[0].score if search_results else 0,
                }

            # Check if we have good coverage
            successful_searches = sum(1 for r in results.values() if r["found"])
            coverage_rate = successful_searches / len(results) if results else 0

            logger.info("📊 Database Verification:")
            for query, result in results.items():
                status = "✅" if result["found"] else "❌"
                logger.info(
                    f"   {status} '{query}': {result['count']} results (score: {result['top_score']:.3f})"
                )

            logger.info(f"   Coverage Rate: {coverage_rate:.1%}")

            return coverage_rate > 0.8  # Good coverage if >80%

        except Exception as e:
            logger.error(f"❌ Database verification failed: {e}")
            return False

    async def create_deployment_summary(self, success: bool, steps: dict[str, bool]) -> None:
        """Create a comprehensive deployment summary."""
        summary = {
            "deployment_date": datetime.now().isoformat(),
            "overall_success": success,
            "steps_completed": steps,
            "system_version": "Comprehensive Horizon Europe RAG v2.0",
            "components": [
                "Enhanced Call-Specific RAG",
                "Comprehensive Document Processing",
                "Vector Database Integration",
                "Intelligent Intent Routing",
            ],
            "documentation_coverage": [
                "Horizon Europe Work Programmes",
                "Programme Guides",
                "Call Texts and Topics",
                "FAQs and Eligibility Criteria",
                "Application Procedures",
            ],
        }

        summary_file = (
            self.test_reports_dir
            / f"deployment_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"📋 Deployment summary saved to: {summary_file}")

        # Print final status
        logger.info("")
        logger.info("🎯 DEPLOYMENT SUMMARY:")
        logger.info("=" * 50)

        for step, completed in steps.items():
            status = "✅" if completed else "❌"
            logger.info(f"{status} {step}")

        logger.info("")
        if success:
            logger.info("🎉 COMPREHENSIVE SYSTEM DEPLOYMENT SUCCESSFUL!")
            logger.info("")
            logger.info("💡 The system is now ready to answer questions about:")
            logger.info("   • Specific Horizon Europe calls and topics")
            logger.info("   • Cluster-specific funding opportunities")
            logger.info("   • Eligibility criteria and requirements")
            logger.info("   • Application procedures and deadlines")
            logger.info("   • Any Horizon Europe-related question")
        else:
            logger.error("💥 DEPLOYMENT FAILED!")
            logger.info("")
            logger.info("🔧 Check the deployment.log for detailed error information")
            logger.info("💡 Common issues:")
            logger.info("   • Database connection problems")
            logger.info("   • API key configuration")
            logger.info("   • Document download permissions")

    async def deploy_comprehensive_system(self) -> bool:
        """Run the complete deployment process."""
        deployment_steps = {}

        try:
            # Step 1: Download documents
            deployment_steps["download_documents"] = await self.download_all_documents()
            if not deployment_steps["download_documents"]:
                logger.error("❌ Document download failed - stopping deployment")
                await self.create_deployment_summary(False, deployment_steps)
                return False

            # Step 2: Process documents
            deployment_steps["process_documents"] = await self.process_documents()
            if not deployment_steps["process_documents"]:
                logger.error("❌ Document processing failed - stopping deployment")
                await self.create_deployment_summary(False, deployment_steps)
                return False

            # Step 3: Ingest documents
            deployment_steps["ingest_documents"] = await self.ingest_documents()
            if not deployment_steps["ingest_documents"]:
                logger.error("❌ Document ingestion failed - stopping deployment")
                await self.create_deployment_summary(False, deployment_steps)
                return False

            # Step 4: Verify database
            deployment_steps["verify_database"] = await self.verify_database_content()
            if not deployment_steps["verify_database"]:
                logger.warning("⚠️ Database verification issues - continuing with testing")

            # Step 5: Test system
            deployment_steps["test_system"] = await self.test_system()
            if not deployment_steps["test_system"]:
                logger.error("❌ System testing failed")
                await self.create_deployment_summary(False, deployment_steps)
                return False

            # Overall success
            overall_success = all(deployment_steps.values())
            await self.create_deployment_summary(overall_success, deployment_steps)

            return overall_success

        except Exception as e:
            logger.error(f"💥 Deployment process failed with exception: {e}")
            import traceback

            traceback.print_exc()
            await self.create_deployment_summary(False, deployment_steps)
            return False


async def main():
    """Main deployment function."""
    deployer = ComprehensiveSystemDeployer()

    try:
        success = await deployer.deploy_comprehensive_system()

        if success:
            logger.info("")
            logger.info("🚀 NEXT STEPS:")
            logger.info("   1. Start the FastAPI server: uvicorn app.main:app --reload")
            logger.info("   2. Test the API endpoints with call-specific queries")
            logger.info("   3. Monitor system performance and adjust as needed")
            logger.info("   4. Consider setting up automated document updates")
            return 0
        else:
            logger.error("💥 Deployment failed - check logs for details")
            return 1

    except KeyboardInterrupt:
        logger.info("⏹️ Deployment interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"💥 Unexpected deployment error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
