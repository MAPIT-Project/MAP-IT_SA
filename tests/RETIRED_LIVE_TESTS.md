# Retired bulk live-response tests

The bounded, data-backed tool scenarios replace the old live-response suite.
Offline unit tests and recorded report/scenario inputs remain in the repository.

- Removed 942 live test functions in 154 test classes, representing 1014
  service-dependent cases in the previous parameterized collection.
- Preserved every previously passing test function by static AST comparison.
  That comparison is an inventory check, not a pytest result.
- Removed 40 collection-time API health probes, 23 unused live fixtures and
  65 unused imports.
- Deleted 35 live-only pytest modules and 9 standalone live runners.
- Retained shared evaluator/runner classes where offline tests exercise them.
  Their two unbounded command-line entry points were removed.

No tests or real inference were executed as part of retirement. Antigravity
runs validation for the resulting suite.

## Deleted live-only pytest modules

- `tests/quality/test_scenario_001_search_open_calls_basic.py`
- `tests/quality/test_scenario_002_search_calls_with_filters.py`
- `tests/quality/test_scenario_004_search_projects_by_topic.py`
- `tests/quality/test_scenario_006_organization_project_search.py`
- `tests/quality/test_scenario_007_programme_statistics.py`
- `tests/quality/test_scenario_008_country_statistics.py`
- `tests/quality/test_scenario_009_find_partners_by_expertise.py`
- `tests/quality/test_scenario_010_collaboration_network.py`
- `tests/quality/test_scenario_011_budget_benchmark.py`
- `tests/quality/test_scenario_012_calculate_budget.py`
- `tests/quality/test_scenario_013_generate_timeline.py`
- `tests/quality/test_scenario_014_consortium_patterns.py`
- `tests/quality/test_scenario_015_progressive_profile.py`
- `tests/quality/test_scenario_015_search_work_programmes.py`
- `tests/quality/test_scenario_016_horizon_europe_full_flow.py`
- `tests/quality/test_scenario_017_erasmus_eligibility.py`
- `tests/quality/test_scenario_018_erasmus_budget.py`
- `tests/quality/test_scenario_019_creative_europe_eligibility.py`
- `tests/quality/test_scenario_020_creative_europe_calls.py`
- `tests/quality/test_scenario_021_eu4health_eligibility.py`
- `tests/quality/test_scenario_022_eu4health_topics.py`
- `tests/quality/test_scenario_023_digital_europe_eligibility.py`
- `tests/quality/test_scenario_024_digital_europe_vs_horizon.py`
- `tests/quality/test_scenario_025_life_eligibility.py`
- `tests/quality/test_scenario_026_life_budget.py`
- `tests/quality/test_scenario_027_multi_programme_search.py`
- `tests/quality/test_scenario_028_multi_part_eligibility_calls_budget.py`
- `tests/quality/test_scenario_029_comparison_recommendation.py`
- `tests/quality/test_scenario_030_context_preservation.py`
- `tests/quality/test_scenario_031_numbered_reference.py`
- `tests/quality/test_scenario_033_clarification_needed.py`
- `tests/quality/test_scenario_034_implicit_intent.py`
- `tests/test_ai_quality/test_live_response_quality.py`
- `tests/test_conversation_scenarios.py`
- `tests/test_real_tools.py`

## Deleted standalone runners

- `tests/quality/execute_scenario_009.py`
- `tests/quality/execute_scenario_010.py`
- `tests/quality/execute_scenario_011.py`
- `tests/quality/run_final_verification.py`
- `tests/quality/run_scenario_025.py`
- `tests/quality/run_scenario_026.py`
- `tests/quality/run_scenario_029.py`
- `tests/quality/run_single_scenario.py`
- `tests/test_conversation_scenarios_live.py`

## Mixed modules retaining offline tests

- `tests/quality/test_phase1_scenarios.py`: 5 live test functions removed.
- `tests/quality/test_phase2_scenarios.py`: 5 live test functions removed.
- `tests/quality/test_phase3_scenarios.py`: 5 live test functions removed.
- `tests/quality/test_phase4_scenarios.py`: 5 live test functions removed.
- `tests/quality/test_phase5_scenarios.py`: 5 live test functions removed.
- `tests/quality/test_prompt_001_horizon_structure.py`: 4 live test functions removed.
- `tests/quality/test_prompt_002_thematic_fields.py`: 4 live test functions removed.
- `tests/quality/test_prompt_003_msca.py`: 5 live test functions removed.
- `tests/quality/test_prompt_004_clusters_missions.py`: 4 live test functions removed.
- `tests/quality/test_prompt_005_instruments.py`: 4 live test functions removed.
- `tests/quality/test_prompt_006_after_he.py`: 4 live test functions removed.
- `tests/quality/test_prompt_007_health_calls.py`: 4 live test functions removed.
- `tests/quality/test_prompt_008_ai_calls.py`: 4 live test functions removed.
- `tests/quality/test_prompt_009_climate_calls.py`: 4 live test functions removed.
- `tests/quality/test_prompt_010_cluster5_ria.py`: 4 live test functions removed.
- `tests/quality/test_prompt_011_turkey_aerospace.py`: 4 live test functions removed.
- `tests/quality/test_prompt_012_austria_agri.py`: 4 live test functions removed.
- `tests/quality/test_prompt_013_japan_eligibility.py`: 4 live test functions removed.
- `tests/quality/test_prompt_014_sme_climate.py`: 4 live test functions removed.
- `tests/quality/test_prompt_015_ngo_climate.py`: 4 live test functions removed.
- `tests/quality/test_prompt_016_local_gov.py`: 4 live test functions removed.
- `tests/quality/test_prompt_017_ai_projects.py`: 4 live test functions removed.
- `tests/quality/test_prompt_018_industry40_agri.py`: 4 live test functions removed.
- `tests/quality/test_prompt_019_soil_regeneration.py`: 4 live test functions removed.
- `tests/quality/test_prompt_020_territorial_resilience.py`: 4 live test functions removed.
- `tests/quality/test_prompt_021_cultural_heritage.py`: 4 live test functions removed.
- `tests/quality/test_prompt_022_water_health.py`: 4 live test functions removed.
- `tests/quality/test_prompt_023_german_actors.py`: 4 live test functions removed.
- `tests/quality/test_prompt_024_turkish_actors.py`: 4 live test functions removed.
- `tests/quality/test_prompt_025_consortium_size.py`: 4 live test functions removed.
- `tests/quality/test_prompt_026_cluster2_coordinators.py`: 4 live test functions removed.
- `tests/quality/test_prompt_027_nonuni_coordinators.py`: 3 live test functions removed.
- `tests/quality/test_prompt_028_country_diversity.py`: 3 live test functions removed.
- `tests/quality/test_prompt_029_nordic_green_energy.py`: 3 live test functions removed.
- `tests/quality/test_prompt_030_spain_municipal.py`: 3 live test functions removed.
- `tests/quality/test_prompt_031_cluster6_ia_stats.py`: 4 live test functions removed.
- `tests/quality/test_prompt_032_east_germany_democracy.py`: 3 live test functions removed.
- `tests/quality/test_prompt_033_ict_water_sensors.py`: 3 live test functions removed.
- `tests/quality/test_prompt_034_policy_evaluation.py`: 4 live test functions removed.
- `tests/quality/test_prompt_035_erc_vs_eic.py`: 4 live test functions removed.
- `tests/quality/test_prompt_036_ria_vs_ia.py`: 4 live test functions removed.
- `tests/quality/test_scenario_001_programme_discovery.py`: 4 live test functions removed.
- `tests/quality/test_scenario_002_programme_comparison.py`: 5 live test functions removed.
- `tests/quality/test_scenario_003_get_call_details.py`: 11 live test functions removed.
- `tests/quality/test_scenario_003_programme_recommendation.py`: 5 live test functions removed.
- `tests/quality/test_scenario_004_eligibility_routing.py`: 6 live test functions removed.
- `tests/quality/test_scenario_005_full_proposal_journey.py`: 6 live test functions removed.
- `tests/quality/test_scenario_005_semantic_project_search.py`: 11 live test functions removed.
- `tests/quality/test_scenario_006_budget_iteration.py`: 6 live test functions removed.
- `tests/quality/test_scenario_007_timeline_refinement.py`: 6 live test functions removed.
- `tests/quality/test_scenario_008_consortium_building.py`: 6 live test functions removed.
- `tests/quality/test_scenario_032_topic_refinement.py`: 13 live test functions removed.
- `tests/quality/test_scenario_035_non_eu_country.py`: 3 live test functions removed.
- `tests/quality/test_scenario_036_outdated_programme.py`: 6 live test functions removed.
- `tests/quality/test_scenario_037_very_specific_niche.py`: 3 live test functions removed.
- `tests/quality/test_scenario_038_first_time_applicant.py`: 7 live test functions removed.
- `tests/quality/test_scenario_039_urgent_deadline_query.py`: 7 live test functions removed.
- `tests/quality/test_scenario_040_no_expired_calls.py`: 8 live test functions removed.
- `tests/quality/test_scenario_041_deadline_accuracy.py`: 8 live test functions removed.
- `tests/quality/test_scenario_042_budget_accuracy.py`: 9 live test functions removed.
- `tests/quality/test_scenario_043_project_data_completeness.py`: 14 live test functions removed.
- `tests/quality/test_scenario_044_project_links_working.py`: 11 live test functions removed.
- `tests/quality/test_scenario_045_2025_priorities.py`: 13 live test functions removed.
- `tests/quality/test_scenario_046_erc_success_rate_accuracy.py`: 13 live test functions removed.
- `tests/quality/test_scenario_047_work_programme_version.py`: 15 live test functions removed.
- `tests/quality/test_scenario_048_erasmus_guide_version.py`: 15 live test functions removed.
- `tests/quality/test_scenario_049_neo4j_unavailable.py`: 6 live test functions removed.
- `tests/quality/test_scenario_050_vector_search_fails.py`: 1 live test functions removed.
- `tests/quality/test_scenario_052_very_long_query.py`: 2 live test functions removed.
- `tests/quality/test_scenario_053_special_characters.py`: 2 live test functions removed.
- `tests/quality/test_scenario_055_no_matching_calls.py`: 4 live test functions removed.
- `tests/quality/test_scenario_056_no_matching_projects.py`: 4 live test functions removed.
- `tests/quality/test_scenario_057_self_correction.py`: 2 live test functions removed.
- `tests/quality/test_scenario_058_simple_query_speed.py`: 2 live test functions removed.
- `tests/quality/test_scenario_059_complex_query_speed.py`: 2 live test functions removed.
- `tests/quality/test_scenario_060_actionable_guidance.py`: 9 live test functions removed.
- `tests/quality/test_scenario_061_source_attribution.py`: 12 live test functions removed.
- `tests/quality/test_scenario_062_streaming_works.py`: 10 live test functions removed.
- `tests/quality/test_scenario_063_tool_progress_visible.py`: 13 live test functions removed.
- `tests/test_advanced_conversation_scenarios.py`: 1 live test functions removed.
- `tests/test_advanced_flows_quality_baseline.py`: 2 live test functions removed.
- `tests/test_cross_programme_validation.py`: 5 live test functions removed.
- `tests/test_goal_achievement_validation.py`: 3 live test functions removed.
- `tests/test_personalization_validation.py`: 4 live test functions removed.
- `tests/test_production_quality_validation.py`: 2 live test functions removed.
- `tests/test_quality_baseline.py`: 3 live test functions removed.
