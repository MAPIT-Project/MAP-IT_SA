#!/usr/bin/env python3
"""
System Update Script for Horizon Europe Call Search

This script provides automated and semi-automated methods to update
the system with new clusters, technologies, and programme specifics.
"""

import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import sys

class SystemUpdater:
    """Automated system updater for adding new capabilities."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.config_files = {
            'intelligent_parser': self.base_dir / 'app' / 'services' / 'intelligent_query_parser.py',
            'ai_parser': self.base_dir / 'app' / 'services' / 'ai_query_parser.py',
            'enhanced_search': self.base_dir / 'app' / 'services' / 'enhanced_call_search.py'
        }
        
    def read_file(self, file_path: Path) -> str:
        """Read file content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"❌ File not found: {file_path}")
            return ""
    
    def write_file(self, file_path: Path, content: str):
        """Write file content."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Updated: {file_path}")
        except Exception as e:
            print(f"❌ Error writing file: {e}")
    
    def add_cluster_support(self, cluster_number: int, cluster_name: str, keywords: List[str]):
        """Add support for a new Horizon Europe cluster."""
        print(f"🔄 Adding support for Cluster {cluster_number}: {cluster_name}")
        
        # Update intelligent query parser
        self._update_intelligent_parser_cluster(cluster_number, cluster_name, keywords)
        
        # Update AI parser
        self._update_ai_parser_cluster(cluster_number, cluster_name, keywords)
        
        # Update enhanced search
        self._update_enhanced_search_cluster(cluster_number, cluster_name)
        
        print(f"✅ Cluster {cluster_number} support added successfully!")
    
    def _update_intelligent_parser_cluster(self, cluster_number: int, cluster_name: str, keywords: List[str]):
        """Update intelligent query parser with cluster support."""
        file_path = self.config_files['intelligent_parser']
        content = self.read_file(file_path)
        
        if not content:
            return
        
        # Add to domain_patterns
        pattern_name = f"cluster_{cluster_number}"
        patterns = [f"r'cluster\\s*{cluster_number}'"]
        patterns.extend([f"r'{keyword.lower().replace(' ', '.*')}'" for keyword in keywords])
        
        pattern_entry = f"    '{pattern_name}': [{', '.join(patterns)}],\n"
        
        # Find domain_patterns section
        domain_start = content.find("domain_patterns = {")
        if domain_start == -1:
            print("❌ Could not find domain_patterns in intelligent parser")
            return
        
        # Find the end of domain_patterns
        domain_end = content.find("}", domain_start)
        if domain_end == -1:
            print("❌ Could not find end of domain_patterns")
            return
        
        # Insert new pattern
        insert_pos = domain_end
        new_content = content[:insert_pos] + pattern_entry + content[insert_pos:]
        
        self.write_file(file_path, new_content)
    
    def _update_ai_parser_cluster(self, cluster_number: int, cluster_name: str, keywords: List[str]):
        """Update AI parser with cluster support."""
        file_path = self.config_files['ai_parser']
        content = self.read_file(file_path)
        
        if not content:
            return
        
        # Add to fallback_patterns domain section
        pattern_name = f"cluster_{cluster_number}"
        patterns = [f"r'cluster\\s*{cluster_number}'"]
        patterns.extend([f"r'{keyword.lower().replace(' ', '.*')}'" for keyword in keywords])
        
        pattern_entry = f"    '{pattern_name}': [{', '.join(patterns)}],\n"
        
        # Find domain section in fallback_patterns
        domain_start = content.find("'domain': {")
        if domain_start == -1:
            print("❌ Could not find domain section in AI parser")
            return
        
        # Find the end of domain section
        domain_end = content.find("}", domain_start)
        if domain_end == -1:
            print("❌ Could not find end of domain section")
            return
        
        # Insert new pattern
        insert_pos = domain_end
        new_content = content[:insert_pos] + pattern_entry + content[insert_pos:]
        
        self.write_file(file_path, new_content)
    
    def _update_enhanced_search_cluster(self, cluster_number: int, cluster_name: str):
        """Update enhanced search with cluster filtering."""
        file_path = self.config_files['enhanced_search']
        content = self.read_file(file_path)
        
        if not content:
            return
        
        # Add cluster filtering logic
        filter_code = f"""
            # Cluster {cluster_number} filter
            if specific_filters.get('cluster_{cluster_number}'):
                domain_filters.append({{"term": {{"programmeDivision": "{cluster_name}"}}}})
                logger.info("🎯 Applying Cluster {cluster_number} filter")
        """
        
        # Find domain filtering section
        domain_start = content.find("# Domain-specific filters from parsed query")
        if domain_start == -1:
            print("❌ Could not find domain filtering section")
            return
        
        # Find a good insertion point (after existing cluster filters)
        insert_point = content.find("domain_filters.append", domain_start)
        if insert_point == -1:
            print("❌ Could not find insertion point for cluster filter")
            return
        
        # Move to end of current cluster filter block
        insert_point = content.find("\n", insert_point)
        while content[insert_point+1:insert_point+5] == "    ":
            insert_point = content.find("\n", insert_point + 1)
        
        new_content = content[:insert_point] + filter_code + content[insert_point:]
        
        self.write_file(file_path, new_content)
    
    def add_technology_support(self, tech_name: str, keywords: List[str]):
        """Add support for a new technology."""
        print(f"🔄 Adding support for technology: {tech_name}")
        
        # Update intelligent query parser
        self._update_intelligent_parser_technology(tech_name, keywords)
        
        # Update AI parser
        self._update_ai_parser_technology(tech_name, keywords)
        
        print(f"✅ Technology '{tech_name}' support added successfully!")
    
    def _update_intelligent_parser_technology(self, tech_name: str, keywords: List[str]):
        """Update intelligent query parser with technology support."""
        file_path = self.config_files['intelligent_parser']
        content = self.read_file(file_path)
        
        if not content:
            return
        
        # Add to tech_patterns
        patterns = [f"r'{keyword.lower().replace(' ', '.*')}'" for keyword in keywords]
        pattern_entry = f"    '{tech_name}': [{', '.join(patterns)}],\n"
        
        # Find tech_patterns section
        tech_start = content.find("tech_patterns = {")
        if tech_start == -1:
            print("❌ Could not find tech_patterns in intelligent parser")
            return
        
        # Find the end of tech_patterns
        tech_end = content.find("}", tech_start)
        if tech_end == -1:
            print("❌ Could not find end of tech_patterns")
            return
        
        # Insert new pattern
        insert_pos = tech_end
        new_content = content[:insert_pos] + pattern_entry + content[insert_pos:]
        
        self.write_file(file_path, new_content)
    
    def _update_ai_parser_technology(self, tech_name: str, keywords: List[str]):
        """Update AI parser with technology support."""
        file_path = self.config_files['ai_parser']
        content = self.read_file(file_path)
        
        if not content:
            return
        
        # Add to domain section in fallback_patterns
        patterns = [f"r'{keyword.lower().replace(' ', '.*')}'" for keyword in keywords]
        pattern_entry = f"    '{tech_name}': [{', '.join(patterns)}],\n"
        
        # Find domain section in fallback_patterns
        domain_start = content.find("'domain': {")
        if domain_start == -1:
            print("❌ Could not find domain section in AI parser")
            return
        
        # Find the end of domain section
        domain_end = content.find("}", domain_start)
        if domain_end == -1:
            print("❌ Could not find end of domain section")
            return
        
        # Insert new pattern
        insert_pos = domain_end
        new_content = content[:insert_pos] + pattern_entry + content[insert_pos:]
        
        self.write_file(file_path, new_content)
    
    def add_programme_support(self, programme_name: str, identifiers: List[str], description: str):
        """Add support for a new programme."""
        print(f"🔄 Adding support for programme: {programme_name}")
        
        # Update enhanced search programme mappings
        self._update_enhanced_search_programme(programme_name, identifiers, description)
        
        print(f"✅ Programme '{programme_name}' support added successfully!")
    
    def _update_enhanced_search_programme(self, programme_name: str, identifiers: List[str], description: str):
        """Update enhanced search with programme support."""
        file_path = self.config_files['enhanced_search']
        content = self.read_file(file_path)
        
        if not content:
            return
        
        # Add to programme_mappings
        mapping_entries = []
        for identifier in identifiers:
            mapping_entries.append(f"    '{identifier.upper()}': '{programme_name}',")
        
        mapping_block = "\n".join(mapping_entries) + "\n"
        
        # Find programme_mappings section
        mappings_start = content.find("programme_mappings = {")
        if mappings_start == -1:
            print("❌ Could not find programme_mappings in enhanced search")
            return
        
        # Find the end of programme_mappings
        mappings_end = content.find("}", mappings_start)
        if mappings_end == -1:
            print("❌ Could not find end of programme_mappings")
            return
        
        # Insert new mappings
        insert_pos = mappings_end
        new_content = content[:insert_pos] + mapping_block + content[insert_pos:]
        
        self.write_file(file_path, new_content)
    
    def generate_test_cases(self, feature_type: str, name: str, test_questions: List[str]):
        """Generate test cases for new features."""
        test_file = self.base_dir / 'tests' / f'test_{feature_type}_{name.lower().replace(" ", "_")}.py'
        
        test_content = f'''"""
Test cases for {feature_type}: {name}
"""

import pytest
from app.services.enhanced_call_search import EnhancedCallSearchService

def test_{feature_type}_{name.lower().replace(" ", "_")}_detection():
    """Test that {name} queries are properly detected."""
    service = EnhancedCallSearchService()
    
    test_queries = [
        {test_questions}
    ]
    
    for query in test_queries:
        result = service.search_calls_enhanced(query, max_results=5)
        assert result['status'] == 'success'
        assert len(result['results']) > 0, f"No results found for query: {{query}}"
        assert '{name.lower()}' in str(result['search_metadata']['filters_applied']).lower()

if __name__ == "__main__":
    test_{feature_type}_{name.lower().replace(" ", "_")}_detection()
    print("✅ All tests passed!")
'''
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        print(f"✅ Test cases generated: {test_file}")

def main():
    """Main function for the update script."""
    parser = argparse.ArgumentParser(description="Update Horizon Europe Call Search System")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Cluster command
    cluster_parser = subparsers.add_parser('cluster', help='Add cluster support')
    cluster_parser.add_argument('number', type=int, help='Cluster number')
    cluster_parser.add_argument('name', help='Cluster name')
    cluster_parser.add_argument('keywords', nargs='+', help='Cluster keywords')
    
    # Technology command
    tech_parser = subparsers.add_parser('technology', help='Add technology support')
    tech_parser.add_argument('name', help='Technology name')
    tech_parser.add_argument('keywords', nargs='+', help='Technology keywords')
    
    # Programme command
    prog_parser = subparsers.add_parser('programme', help='Add programme support')
    prog_parser.add_argument('name', help='Programme name')
    prog_parser.add_argument('identifiers', nargs='+', help='Programme identifiers')
    prog_parser.add_argument('--description', default='', help='Programme description')
    
    args = parser.parse_args()
    
    updater = SystemUpdater()
    
    if args.command == 'cluster':
        updater.add_cluster_support(args.number, args.name, args.keywords)
        
        # Generate test questions
        test_questions = [
            f"What are open calls in Cluster {args.number} for {args.name.lower()}?",
            f"Forthcoming opportunities in {args.name}",
            f"Recent {args.name} research calls"
        ]
        updater.generate_test_cases('cluster', args.name, test_questions)
        
    elif args.command == 'technology':
        updater.add_technology_support(args.name, args.keywords)
        
        # Generate test questions
        test_questions = [
            f"Open calls for {args.name}",
            f"{args.name} research opportunities",
            f"Funding for {args.name} development"
        ]
        updater.generate_test_cases('technology', args.name, test_questions)
        
    elif args.command == 'programme':
        updater.add_programme_support(args.name, args.identifiers, args.description)
        
        # Generate test questions
        test_questions = [
            f"{args.name} funding opportunities",
            f"Calls under {args.name} programme",
            f"{args.name} grants and funding"
        ]
        updater.generate_test_cases('programme', args.name, test_questions)
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()