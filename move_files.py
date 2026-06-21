import os
import shutil

base_dir = r"C:\Synology Drive\2way-sync\work\rag-maker\.tmp\cache"

moves = [
    # guide
    (r"docs\kagi\getting-started\setting-default\orion-iphone-ipad.md", r"guide\kagi_guide_orion_ios_default_search_setup.md"),
    (r"docs\kagi\getting-started\setting-default\orion-mac.md", r"guide\kagi_guide_orion_macos_default_search_setup.md"),
    (r"docs\kagi\getting-started\setting-default\safari-iphone-ipad.md", r"guide\kagi_guide_safari_ios_default_search_setup.md"),
    (r"docs\kagi\getting-started\setting-default\safari-mac.md", r"guide\kagi_guide_safari_macos_default_search_setup.md"),
    (r"docs\kagi\getting-started\setting-default\vanadium-grapheneos.md", r"guide\kagi_guide_vanadium_grapheneos_default_search_setup.md"),
    (r"docs\kagi\getting-started\setting-default\vivaldi-android.md", r"guide\kagi_guide_vivaldi_android_default_search_setup.md"),
    (r"docs\kagi\getting-started\setting-default\vivaldi-desktop.md", r"guide\kagi_guide_vivaldi_desktop_default_search_setup.md"),
    (r"docs\kagi\getting-started\setting-default\vivaldi-ios.md", r"guide\kagi_guide_vivaldi_ios_default_search_setup.md"),
    # appendix
    (r"docs\kagi\legal\pioneer-ticket-raffle.md", r"appendix\kagi_appendix_pioneer_ticket_raffle_terms.md"),
    (r"docs\kagi\mail\index.md", r"appendix\kagi_appendix_mail_faq.md"),
    # guide
    (r"docs\kagi\maps\index.md", r"guide\kagi_guide_maps_features_and_setup.md"),
    (r"docs\kagi\news\index.md", r"guide\kagi_guide_news_features_and_setup.md"),
    (r"docs\kagi\plans\family-plan.md", r"guide\kagi_guide_family_plan_setup_and_features.md"),
    (r"docs\kagi\plans\gift-kagi.md", r"guide\kagi_guide_gift_subscription_purchase_steps.md"),
    (r"docs\kagi\plans\legacy-team-plan.md", r"guide\kagi_guide_legacy_team_plan_management.md"),
    # reference
    (r"docs\kagi\plans\payment-methods.md", r"reference\kagi_reference_payment_methods_and_billing.md"),
    # guide
    (r"docs\kagi\plans\plan-management.md", r"guide\kagi_guide_plan_management_and_cancellation.md"),
    # reference
    (r"docs\kagi\plans\plan-types.md", r"reference\kagi_reference_subscription_plan_types_and_pricing.md"),
    # guide
    (r"docs\kagi\plans\team-plan.md", r"guide\kagi_guide_team_plan_setup_and_management.md"),
    # reference
    (r"docs\kagi\plans\ultimate-plan.md", r"reference\kagi_reference_ultimate_plan_benefits_and_pricing.md"),
    # introduction
    (r"docs\kagi\privacy\anonymity.md", r"introduction\kagi_introduction_privacy_and_anonymity_concept.md"),
    # reference
    (r"docs\kagi\privacy\bug-bounty-program.md", r"reference\kagi_reference_bug_bounty_program_guidelines.md"),
    # appendix
    (r"docs\kagi\privacy\content-policy.md", r"appendix\kagi_appendix_content_policy_redirection.md"),
    # reference
    (r"docs\kagi\privacy\cookies.md", r"reference\kagi_reference_cookies_and_client_data_specification.md"),
    (r"docs\kagi\privacy\how-does-privacy-pass-work.md", r"reference\kagi_reference_privacy_pass_cryptographic_architecture.md"),
    # guide
    (r"docs\kagi\privacy\log-in-with-qr-code.md", r"guide\kagi_guide_qr_code_login_setup_and_security.md"),
    (r"docs\kagi\privacy\privacy-pass.md", r"guide\kagi_guide_privacy_pass_setup_and_troubleshooting.md"),
    # introduction
    (r"docs\kagi\privacy\privacy-protection.md", r"introduction\kagi_introduction_privacy_protection_philosophy.md"),
    # guide
    (r"docs\kagi\privacy\private-browser-sessions.md", r"guide\kagi_guide_private_browser_session_link_setup.md"),
    # reference
    (r"docs\kagi\privacy\safe-harbor.md", r"reference\kagi_reference_bug_bounty_legal_safe_harbor.md"),
    # introduction
    (r"docs\kagi\privacy\security.md", r"introduction\kagi_introduction_security_audit_and_bug_bounty_overview.md"),
    # guide
    (r"docs\kagi\privacy\tor.md", r"guide\kagi_guide_tor_onion_service_setup_and_usage.md"),
    (r"docs\kagi\privacy\two-factor-authentication.md", r"guide\kagi_guide_two_factor_authentication_setup_and_management.md"),
    # reference
    (r"docs\kagi\search-details\search-quality.md", r"reference\kagi_reference_search_quality_and_ranking_algorithm.md"),
    (r"docs\kagi\search-details\search-sources.md", r"reference\kagi_reference_search_data_sources_and_integrations.md"),
    (r"docs\kagi\search-details\search-speed.md", r"reference\kagi_reference_search_speed_benchmarks_and_infrastructure.md"),
    (r"docs\kagi\search-details\small-web-in-search-results.md", r"reference\kagi_reference_small_web_integration_in_search_results.md"),
    # guide
    (r"docs\kagi\settings\accessing.md", r"guide\kagi_guide_how_to_access_settings_page.md"),
    # reference
    (r"docs\kagi\settings\account.md", r"reference\kagi_reference_account_settings_items_and_features.md"),
    (r"docs\kagi\settings\advanced.md", r"reference\kagi_reference_advanced_settings_items_and_features.md"),
    (r"docs\kagi\settings\ai.md", r"reference\kagi_reference_ai_search_settings_items.md"),
    (r"docs\kagi\settings\appearance.md", r"reference\kagi_reference_appearance_settings_and_custom_css.md"),
    (r"docs\kagi\settings\assistant.md", r"reference\kagi_reference_assistant_settings_and_customization.md"),
    (r"docs\kagi\settings\billing.md", r"reference\kagi_reference_billing_settings_and_usage_details.md"),
    # guide
    (r"docs\kagi\settings\delete-account.md", r"guide\kagi_guide_account_deletion_process_and_impact.md"),
    # reference
    (r"docs\kagi\settings\general.md", r"reference\kagi_reference_general_search_settings_items.md"),
    (r"docs\kagi\settings\lenses.md", r"reference\kagi_reference_lenses_settings_overview.md"),
    (r"docs\kagi\settings\personalized-results.md", r"reference\kagi_reference_personalized_results_settings_overview.md"),
    (r"docs\kagi\settings\search.md", r"reference\kagi_reference_web_search_settings_items.md"),
    (r"docs\kagi\settings\widgets.md", r"reference\kagi_reference_search_widgets_settings_items.md"),
    # guide
    (r"docs\kagi\sidekick\index.md", r"guide\kagi_guide_sidekick_integration_and_features.md"),
    (r"docs\kagi\summarizer\index.md", r"guide\kagi_guide_summarizer_features_and_usage.md"),
    # appendix
    (r"docs\kagi\support-and-community\blog.md", r"appendix\kagi_appendix_blog_links_and_rss.md"),
    # guide
    (r"docs\kagi\support-and-community\bug-reporting.md", r"guide\kagi_guide_bug_reporting_workflow_and_guidelines.md"),
    # reference
    (r"docs\kagi\support-and-community\community-roles.md", r"reference\kagi_reference_community_roles_and_perks.md"),
    # appendix
    (r"docs\kagi\support-and-community\discord-server.md", r"appendix\kagi_appendix_discord_server_channels_and_link.md"),
    (r"docs\kagi\support-and-community\doggos.md", r"appendix\kagi_appendix_doggos_community_artwork_event.md"),
    (r"docs\kagi\support-and-community\email-support.md", r"appendix\kagi_appendix_email_support_contact_details.md"),
    (r"docs\kagi\support-and-community\index.md", r"appendix\kagi_appendix_support_community_and_social_links.md"),
    (r"docs\kagi\support-and-community\open-source.md", r"appendix\kagi_appendix_open_source_projects_list.md"),
    # introduction
    (r"docs\kagi\support-and-community\share-kagi.md", r"introduction\kagi_introduction_how_to_share_kagi_with_others.md"),
    # guide
    (r"docs\kagi\translate\index.md", r"guide\kagi_guide_translate_features_and_usage.md"),
    # reference
    (r"docs\kagi\translate\url-parameters.md", r"reference\kagi_reference_translate_url_parameters_specification.md"),
    # introduction
    (r"docs\kagi\why-kagi\ai-philosophy.md", r"introduction\kagi_introduction_ai_integration_philosophy.md"),
    (r"docs\kagi\why-kagi\kagi-vs-brave.md", r"introduction\kagi_introduction_comparison_kagi_vs_brave_search.md"),
    (r"docs\kagi\why-kagi\kagi-vs-competition.md", r"introduction\kagi_introduction_comparison_kagi_vs_competitors.md"),
    (r"docs\kagi\why-kagi\kagi-vs-duckduckgo.md", r"introduction\kagi_introduction_comparison_kagi_vs_duckduckgo.md"),
    (r"docs\kagi\why-kagi\kagi-vs-google.md", r"introduction\kagi_introduction_comparison_kagi_vs_google.md"),
    (r"docs\kagi\why-kagi\noads.md", r"introduction\kagi_introduction_ad_free_philosophy_and_benefits.md"),
    (r"docs\kagi\why-kagi\why-pay-for-search.md", r"introduction\kagi_introduction_why_pay_for_search_value_proposition.md"),
]

for src_rel, dst_rel in moves:
    src_path = os.path.join(base_dir, src_rel)
    dst_path = os.path.join(base_dir, dst_rel)
    
    if os.path.exists(src_path):
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        # Move the file
        shutil.move(src_path, dst_path)
        print(f"Moved: {src_rel} -> {dst_rel}")
    else:
        print(f"Not found: {src_rel}")
