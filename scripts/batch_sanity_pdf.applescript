tell application "Microsoft Word"
  set displayAlerts to false
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/1_5_line_spacing_id_paraid_overflow_24_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/1_5_line_spacing_id_paraid_overflow_24_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/24_id_paraid_overflow_alternate_content_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/24_id_paraid_overflow_alternate_content_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/24_id_paraid_overflow_blue_bold_centered_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/24_id_paraid_overflow_blue_bold_centered_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_increase_indent_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_increase_indent_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/alternate_content_anchor_images_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/alternate_content_anchor_images_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/blue_bold_centered_demo_id_paraid_overflow_blue_centered_title_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/blue_bold_centered_demo_id_paraid_overflow_blue_centered_title_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/blue_centered_title_demo_style_default_missing_blue_italic_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/blue_centered_title_demo_style_default_missing_blue_italic_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/blue_italic_text_demo_id_paraid_overflow_blue_underline_combo_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/blue_italic_text_demo_id_paraid_overflow_blue_underline_combo_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/blue_underline_combo_demo_id_paraid_overflow_bold_and_italic_combo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/blue_underline_combo_demo_id_paraid_overflow_bold_and_italic_combo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_and_italic_combo_style_default_missing_bold_and_underline_combo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_and_italic_combo_style_default_missing_bold_and_underline_combo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_and_underline_combo_id_paraid_overflow_bold_italic_combined_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_and_underline_combo_id_paraid_overflow_bold_italic_combined_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_italic_combined_demo_id_paraid_overflow_bold_italic_underline_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_italic_combined_demo_id_paraid_overflow_bold_italic_underline_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_italic_underline_demo_id_paraid_overflow_bold_red_text_combo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_italic_underline_demo_id_paraid_overflow_bold_red_text_combo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_red_text_combo_id_paraid_overflow_bold_superscript_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_red_text_combo_id_paraid_overflow_bold_superscript_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_superscript_demo_style_default_missing_bold_text_formatting_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_superscript_demo_style_default_missing_bold_text_formatting_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_text_formatting_demo_id_paraid_overflow_2_bold_text_formatting_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_text_formatting_demo_id_paraid_overflow_2_bold_text_formatting_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_text_formatting_demo_id_paraid_overflow_bold_underline_combined_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_text_formatting_demo_id_paraid_overflow_bold_underline_combined_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_underline_combined_demo_id_paraid_overflow_bold_underline_highlight_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_underline_combined_demo_id_paraid_overflow_bold_underline_highlight_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_underline_highlight_demo_id_paraid_overflow_book_catalog_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bold_underline_highlight_demo_id_paraid_overflow_book_catalog_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/book_catalog_id_paraid_overflow_book_catalog_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/book_catalog_id_paraid_overflow_book_catalog_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/book_catalog_table_budget_report_q1_2026_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/book_catalog_table_budget_report_q1_2026_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/book_catalog_table_budget_report_q1_2026_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/book_catalog_table_budget_report_q1_2026_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/budget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/budget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/budget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/budget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bullet_list_bold_demo_id_paraid_overflow_bullet_list_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bullet_list_bold_demo_id_paraid_overflow_bullet_list_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bullet_list_demo_id_paraid_overflow_calibri_bold_italic_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/bullet_list_demo_id_paraid_overflow_calibri_bold_italic_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/calibri_bold_italic_demo_id_paraid_overflow_calibri_font_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/calibri_bold_italic_demo_id_paraid_overflow_calibri_font_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/calibri_font_demo_id_paraid_overflow_2_calibri_font_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/calibri_font_demo_id_paraid_overflow_2_calibri_font_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/calibri_font_demo_id_paraid_overflow_calibri_heading_2_right_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/calibri_font_demo_id_paraid_overflow_calibri_heading_2_right_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/calibri_heading_2_right_id_paraid_overflow_center_aligned_bold_text_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/calibri_heading_2_right_id_paraid_overflow_center_aligned_bold_text_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/center_aligned_bold_text_id_paraid_overflow_center_alignment_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/center_aligned_bold_text_id_paraid_overflow_center_alignment_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/center_alignment_demo_id_paraid_overflow_2_center_alignment_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/center_alignment_demo_id_paraid_overflow_2_center_alignment_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/center_alignment_demo_id_paraid_overflow_center_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/center_alignment_demo_id_paraid_overflow_center_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/center_bold_demo_id_paraid_overflow_clear_formatting_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/center_bold_demo_id_paraid_overflow_clear_formatting_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/clear_formatting_demo_id_paraid_overflow_comments_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/clear_formatting_demo_id_paraid_overflow_comments_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/clear_formatting_demo_id_paraid_overflow_contract_review_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/clear_formatting_demo_id_paraid_overflow_contract_review_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/comments_complex_style_attr_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/comments_complex_style_attr_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/complex_style_attr_contract_review_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/complex_style_attr_contract_review_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/document_100_ultimate_demo_id_paraid_overflow_docx_lots_of_comments_addition_redline_addition_v_removal_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/document_100_ultimate_demo_id_paraid_overflow_docx_lots_of_comments_addition_redline_addition_v_removal_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/document_100_ultimate_demo_id_paraid_overflow_double_spacing_bold_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/document_100_ultimate_demo_id_paraid_overflow_double_spacing_bold_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/docx_lots_of_comments_addition_docx_lots_of_comments_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/docx_lots_of_comments_addition_docx_lots_of_comments_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/docx_lots_of_comments_addition_redline_addition_v_removal_docx_lots_of_comments_addition_redline_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/docx_lots_of_comments_addition_redline_addition_v_removal_docx_lots_of_comments_addition_redline_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/docx_lots_of_comments_addition_redline_docx_lots_of_comments_addition_removal_redline_removal_v_addition_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/docx_lots_of_comments_addition_redline_docx_lots_of_comments_addition_removal_redline_removal_v_addition_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/docx_lots_of_comments_addition_removal_docx_lots_of_comments_addition_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/docx_lots_of_comments_addition_removal_docx_lots_of_comments_addition_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/docx_lots_of_comments_addition_removal_redline_docx_lots_of_comments_addition_removal_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/docx_lots_of_comments_addition_removal_redline_docx_lots_of_comments_addition_removal_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/docx_lots_of_comments_addition_removal_redline_removal_v_addition_docx_lots_of_comments_addition_removal_redline_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/docx_lots_of_comments_addition_removal_redline_removal_v_addition_docx_lots_of_comments_addition_removal_redline_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/docx_lots_of_comments_double_spacing_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/docx_lots_of_comments_double_spacing_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/double_spacing_bold_demo_id_paraid_overflow_eigenpal_docx_editor_suggesting_mixed_edits_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/double_spacing_bold_demo_id_paraid_overflow_eigenpal_docx_editor_suggesting_mixed_edits_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/eigenpal_docx_editor_suggesting_mixed_edits_employee_directory_table_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/eigenpal_docx_editor_suggesting_mixed_edits_employee_directory_table_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/employee_directory_table_2_employee_directory_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/employee_directory_table_2_employee_directory_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/employee_directory_table_employee_review_john_smith_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/employee_directory_table_employee_review_john_smith_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/employee_directory_table_employee_review_john_smith_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/employee_directory_table_employee_review_john_smith_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/employee_review_john_smith_suggesting_insertions_font_color_blue_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/employee_review_john_smith_suggesting_insertions_font_color_blue_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_color_blue_demo_style_default_missing_font_color_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_color_blue_demo_style_default_missing_font_color_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_color_demo_style_default_missing_font_family_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_color_demo_style_default_missing_font_family_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_family_demo_id_paraid_overflow_font_size_12_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_family_demo_id_paraid_overflow_font_size_12_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_size_12_demo_id_paraid_overflow_font_size_18_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_size_12_demo_id_paraid_overflow_font_size_18_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_size_18_demo_style_default_missing_font_size_24_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_size_18_demo_style_default_missing_font_size_24_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_size_24_demo_id_paraid_overflow_font_size_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_size_24_demo_id_paraid_overflow_font_size_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_size_demo_id_paraid_overflow_footnotes_sample_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_size_demo_id_paraid_overflow_footnotes_sample_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_size_demo_id_paraid_overflow_green_bold_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/font_size_demo_id_paraid_overflow_green_bold_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/footnotes_sample_gdocs_comments_export_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/footnotes_sample_gdocs_comments_export_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/gdocs_comments_export_green_bold_text_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/gdocs_comments_export_green_bold_text_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/green_bold_text_demo_id_paraid_overflow_green_highlight_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/green_bold_text_demo_id_paraid_overflow_green_highlight_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/green_highlight_demo_id_paraid_overflow_green_underline_bullet_list_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/green_highlight_demo_id_paraid_overflow_green_underline_bullet_list_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/green_underline_bullet_list_id_paraid_overflow_header_no_rels_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/green_underline_bullet_list_id_paraid_overflow_header_no_rels_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/green_underline_bullet_list_id_paraid_overflow_heading_1_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/green_underline_bullet_list_id_paraid_overflow_heading_1_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/header_no_rels_heading_1_bold_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/header_no_rels_heading_1_bold_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_1_bold_demo_id_paraid_overflow_heading_1_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_1_bold_demo_id_paraid_overflow_heading_1_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_1_style_demo_id_paraid_overflow_heading_2_center_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_1_style_demo_id_paraid_overflow_heading_2_center_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_2_center_demo_id_paraid_overflow_heading_2_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_2_center_demo_id_paraid_overflow_heading_2_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_2_style_demo_id_paraid_overflow_heading_3_center_italic_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_2_style_demo_id_paraid_overflow_heading_3_center_italic_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_3_center_italic_id_paraid_overflow_heading_3_style_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_3_center_italic_id_paraid_overflow_heading_3_style_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_3_style_demo_id_paraid_overflow_2_heading_3_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_3_style_demo_id_paraid_overflow_2_heading_3_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_3_style_demo_id_paraid_overflow_heading_4_right_italic_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_3_style_demo_id_paraid_overflow_heading_4_right_italic_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_4_right_italic_id_paraid_overflow_heading_4_style_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_4_right_italic_id_paraid_overflow_heading_4_style_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_4_style_demo_id_paraid_overflow_2_heading_4_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_4_style_demo_id_paraid_overflow_2_heading_4_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_4_style_demo_id_paraid_overflow_helvetica_font_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/heading_4_style_demo_id_paraid_overflow_helvetica_font_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/helvetica_font_demo_style_default_missing_hr_onboarding_checklist_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/helvetica_font_demo_style_default_missing_hr_onboarding_checklist_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/hr_onboarding_checklist_table_I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/hr_onboarding_checklist_table_I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/increase_indent_demo_id_paraid_overflow_insert_link_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/increase_indent_demo_id_paraid_overflow_insert_link_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/italic_and_underline_combo_style_default_missing_italic_subscript_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/italic_and_underline_combo_style_default_missing_italic_subscript_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/italic_subscript_demo_style_default_missing_italic_text_formatting_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/italic_subscript_demo_style_default_missing_italic_text_formatting_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/italic_text_formatting_demo_id_paraid_overflow_2_italic_text_formatting_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/italic_text_formatting_demo_id_paraid_overflow_2_italic_text_formatting_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/italic_text_formatting_demo_id_paraid_overflow_italic_underline_combined_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/italic_text_formatting_demo_id_paraid_overflow_italic_underline_combined_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/italic_underline_combined_demo_id_paraid_overflow_justified_underline_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/italic_underline_combined_demo_id_paraid_overflow_justified_underline_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/justified_underline_demo_id_paraid_overflow_justify_alignment_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/justified_underline_demo_id_paraid_overflow_justify_alignment_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/justify_alignment_demo_id_paraid_overflow_2_justify_alignment_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/justify_alignment_demo_id_paraid_overflow_2_justify_alignment_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/justify_alignment_demo_id_paraid_overflow_large_font_size_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/justify_alignment_demo_id_paraid_overflow_large_font_size_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/large_font_size_demo_id_paraid_overflow_left_alignment_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/large_font_size_demo_id_paraid_overflow_left_alignment_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/left_alignment_demo_id_paraid_overflow_line_spacing_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/left_alignment_demo_id_paraid_overflow_line_spacing_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/marketing_strategy_2026_suggesting_insertions_meeting_agenda_table_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/marketing_strategy_2026_suggesting_insertions_meeting_agenda_table_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/mcdoc_meeting_agenda_table_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/mcdoc_meeting_agenda_table_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/meeting_agenda_table_2_meeting_agenda_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/meeting_agenda_table_2_meeting_agenda_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/meeting_agenda_table_meeting_minutes_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/meeting_agenda_table_meeting_minutes_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/meeting_minutes_suggesting_insertions_multi_section_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/meeting_minutes_suggesting_insertions_multi_section_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/meeting_minutes_suggesting_insertions_numbered_list_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/meeting_minutes_suggesting_insertions_numbered_list_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/multi_section_nested_table_rowspan_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/multi_section_nested_table_rowspan_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/nested_table_rowspan_numbered_list_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/nested_table_rowspan_numbered_list_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/numbered_list_demo_id_paraid_overflow_numbered_list_italic_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/numbered_list_demo_id_paraid_overflow_numbered_list_italic_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/numbered_list_italic_demo_id_paraid_overflow_numwords_fldsimple_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/numbered_list_italic_demo_id_paraid_overflow_numwords_fldsimple_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/numbered_list_italic_demo_id_paraid_overflow_open_sans_bold_underline_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/numbered_list_italic_demo_id_paraid_overflow_open_sans_bold_underline_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/numwords_fldsimple_ole_object_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/numwords_fldsimple_ole_object_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/ole_object_ooxml_style_link_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/ole_object_ooxml_style_link_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/ooxml_style_link_open_sans_bold_underline_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/ooxml_style_link_open_sans_bold_underline_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/open_sans_bold_underline_id_paraid_overflow_open_sans_font_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/open_sans_bold_underline_id_paraid_overflow_open_sans_font_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/open_sans_font_demo_id_paraid_overflow_2_open_sans_font_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/open_sans_font_demo_id_paraid_overflow_2_open_sans_font_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/open_sans_font_demo_id_paraid_overflow_page_numbering_examples_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/open_sans_font_demo_id_paraid_overflow_page_numbering_examples_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/open_sans_font_demo_id_paraid_overflow_product_roadmap_2026_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/open_sans_font_demo_id_paraid_overflow_product_roadmap_2026_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/page_numbering_examples_potpourritest_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/page_numbering_examples_potpourritest_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/potpourritest_product_roadmap_2026_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/potpourritest_product_roadmap_2026_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_proposal_id_paraid_overflow_project_proposal_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_proposal_id_paraid_overflow_project_proposal_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_tasks_suggesting_insertions_q1_sales_summary_table_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_tasks_suggesting_insertions_q1_sales_summary_table_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_tasks_suggesting_insertions_q1_sales_summary_table_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/project_tasks_suggesting_insertions_q1_sales_summary_table_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/q1_sales_summary_table_2_q1_sales_summary_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/q1_sales_summary_table_2_q1_sales_summary_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/q1_sales_summary_table_quarterly_performance_report_table_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/q1_sales_summary_table_quarterly_performance_report_table_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/quarterly_performance_report_table_2_quarterly_performance_report_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/quarterly_performance_report_table_2_quarterly_performance_report_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/quarterly_performance_report_table_red_bold_heading_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/quarterly_performance_report_table_red_bold_heading_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/red_bold_heading_demo_style_default_missing_red_bold_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/red_bold_heading_demo_style_default_missing_red_bold_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/red_bold_text_demo_id_paraid_overflow_red_heading_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/red_bold_text_demo_id_paraid_overflow_red_heading_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/red_heading_demo_id_paraid_overflow_red_strikethrough_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/red_heading_demo_id_paraid_overflow_red_strikethrough_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/red_strikethrough_demo_style_default_missing_redline_cicerodo_v_plate_30_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/red_strikethrough_demo_style_default_missing_redline_cicerodo_v_plate_30_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/red_strikethrough_demo_style_default_missing_right_align_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/red_strikethrough_demo_style_default_missing_right_align_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/redline_cicerodo_v_plate_30_right_align_bold_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/redline_cicerodo_v_plate_30_right_align_bold_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/right_align_bold_demo_id_paraid_overflow_right_aligned_italic_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/right_align_bold_demo_id_paraid_overflow_right_aligned_italic_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/right_aligned_italic_demo_id_paraid_overflow_right_alignment_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/right_aligned_italic_demo_id_paraid_overflow_right_alignment_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/right_alignment_demo_id_paraid_overflow_2_right_alignment_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/right_alignment_demo_id_paraid_overflow_2_right_alignment_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/roboto_font_demo_id_paraid_overflow_2_roboto_font_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/roboto_font_demo_id_paraid_overflow_2_roboto_font_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/roboto_font_demo_id_paraid_overflow_roboto_underline_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/roboto_font_demo_id_paraid_overflow_roboto_underline_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sample_document_afterword_repaired_word_repaired_sample_document_really_repaired_word_repaired_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sample_document_afterword_repaired_word_repaired_sample_document_really_repaired_word_repaired_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sample_document_really_repaired_word_repaired_sample_document_word_repair_of_our_output_iter2_word_repaired_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sample_document_really_repaired_word_repaired_sample_document_word_repair_of_our_output_iter2_word_repaired_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sample_document_word_repair_of_our_output_word_repaired_sd_2517_localized_heading_styles_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sample_document_word_repair_of_our_output_word_repaired_sd_2517_localized_heading_styles_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sample_document_word_repair_of_our_output_word_repaired_small_font_size_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sample_document_word_repair_of_our_output_word_repaired_small_font_size_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sd_2517_localized_heading_styles_sectpr_headerref_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sd_2517_localized_heading_styles_sectpr_headerref_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sectpr_headerref_single_paragraph_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/sectpr_headerref_single_paragraph_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/single_paragraph_small_font_size_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/single_paragraph_small_font_size_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/small_font_size_demo_id_paraid_overflow_strict01_sdt_controls_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/small_font_size_demo_id_paraid_overflow_strict01_sdt_controls_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/small_font_size_demo_id_paraid_overflow_strikethrough_and_italic_combo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/small_font_size_demo_id_paraid_overflow_strikethrough_and_italic_combo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/strict01_sdt_controls_strict01_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/strict01_sdt_controls_strict01_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/strict01_strikethrough_and_italic_combo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/strict01_strikethrough_and_italic_combo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/strikethrough_and_italic_combo_id_paraid_overflow_strikethrough_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/strikethrough_and_italic_combo_id_paraid_overflow_strikethrough_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/strikethrough_bold_demo_id_paraid_overflow_strikethrough_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/strikethrough_bold_demo_id_paraid_overflow_strikethrough_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/strikethrough_text_demo_id_paraid_overflow_strikethrough_text_formatting_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/strikethrough_text_demo_id_paraid_overflow_strikethrough_text_formatting_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/strikethrough_text_formatting_demo_id_paraid_overflow_subscript_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/strikethrough_text_formatting_demo_id_paraid_overflow_subscript_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/subscript_demo_id_paraid_overflow_subscript_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/subscript_demo_id_paraid_overflow_subscript_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/subscript_demo_style_default_missing_subtitle_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/subscript_demo_style_default_missing_subtitle_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/subtitle_style_demo_id_paraid_overflow_subtitle_style_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/subtitle_style_demo_id_paraid_overflow_subtitle_style_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/subtitle_style_demo_style_default_missing_superscript_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/subtitle_style_demo_style_default_missing_superscript_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/superscript_demo_id_paraid_overflow_2_superscript_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/superscript_demo_id_paraid_overflow_2_superscript_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/superscript_demo_id_paraid_overflow_superscript_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/superscript_demo_id_paraid_overflow_superscript_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/superscript_demo_style_default_missing_support_tickets_summary_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/superscript_demo_style_default_missing_support_tickets_summary_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/superscript_demo_style_default_missing_support_tickets_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/superscript_demo_style_default_missing_support_tickets_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/support_tickets_summary_id_paraid_overflow_support_tickets_table_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/support_tickets_summary_id_paraid_overflow_support_tickets_table_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/support_tickets_summary_id_paraid_overflow_text_highlight_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/support_tickets_summary_id_paraid_overflow_text_highlight_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/support_tickets_table_support_tickets_summary_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/support_tickets_table_support_tickets_summary_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/support_tickets_table_table_bookmark_end_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/support_tickets_table_table_bookmark_end_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/table_bookmark_end_table_vmerge_colspan_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/table_bookmark_end_table_vmerge_colspan_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/table_vmerge_colspan_text_box_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/table_vmerge_colspan_text_box_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/text_box_text_highlight_demo_style_default_missing_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/text_box_text_highlight_demo_style_default_missing_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/text_highlight_demo_style_default_missing_tiff_image_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/text_highlight_demo_style_default_missing_tiff_image_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/text_highlight_demo_style_default_missing_times_new_roman_bold_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/text_highlight_demo_style_default_missing_times_new_roman_bold_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/tiff_image_times_new_roman_bold_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/tiff_image_times_new_roman_bold_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/times_new_roman_bold_id_paraid_overflow_times_new_roman_font_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/times_new_roman_bold_id_paraid_overflow_times_new_roman_font_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/times_new_roman_font_id_paraid_overflow_title_style_centered_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/times_new_roman_font_id_paraid_overflow_title_style_centered_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/title_style_centered_demo_id_paraid_overflow_title_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/title_style_centered_demo_id_paraid_overflow_title_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/title_style_demo_id_paraid_overflow_title_style_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/title_style_demo_id_paraid_overflow_title_style_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/title_style_demo_style_default_missing_track_changes_editing_bullet_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/title_style_demo_style_default_missing_track_changes_editing_bullet_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_editing_bullet_id_paraid_overflow_track_changes_editing_strikethrough_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_editing_bullet_id_paraid_overflow_track_changes_editing_strikethrough_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_editing_strikethrough_id_paraid_overflow_track_changes_suggesting_bold_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_editing_strikethrough_id_paraid_overflow_track_changes_suggesting_bold_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_suggesting_bold_id_paraid_overflow_track_changes_suggesting_calibri_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_suggesting_bold_id_paraid_overflow_track_changes_suggesting_calibri_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_suggesting_calibri_id_paraid_overflow_track_changes_suggesting_center_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_suggesting_calibri_id_paraid_overflow_track_changes_suggesting_center_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_suggesting_center_id_paraid_overflow_track_changes_suggesting_heading_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_suggesting_center_id_paraid_overflow_track_changes_suggesting_heading_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_suggesting_heading_id_paraid_overflow_track_changes_suggesting_italic_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_suggesting_heading_id_paraid_overflow_track_changes_suggesting_italic_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_suggesting_italic_id_paraid_overflow_track_changes_suggesting_title_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_suggesting_italic_id_paraid_overflow_track_changes_suggesting_title_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/underline_text_demo_id_paraid_overflow_underline_text_formatting_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/underline_text_demo_id_paraid_overflow_underline_text_formatting_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/underline_text_formatting_demo_style_default_missing_verdana_bold_large_font_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/underline_text_formatting_demo_style_default_missing_verdana_bold_large_font_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/verdana_font_demo_id_paraid_overflow_2_verdana_font_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/verdana_font_demo_id_paraid_overflow_2_verdana_font_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/verdana_font_demo_id_paraid_overflow_verdana_italic_centered_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/verdana_font_demo_id_paraid_overflow_verdana_italic_centered_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/verdana_italic_centered_demo_id_paraid_overflow_vfdsdfcacawesd_suggesting_mixed_edits_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/verdana_italic_centered_demo_id_paraid_overflow_vfdsdfcacawesd_suggesting_mixed_edits_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/verdana_italic_centered_demo_id_paraid_overflow_word_clean_strict01_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/verdana_italic_centered_demo_id_paraid_overflow_word_clean_strict01_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/vfdsdfcacawesd_suggesting_mixed_edits_yellow_highlight_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/vfdsdfcacawesd_suggesting_mixed_edits_yellow_highlight_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/word_clean_strict01_word_tolerated_broken_media_rel_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/word_clean_strict01_word_tolerated_broken_media_rel_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/word_tolerated_broken_media_rel_word_tolerated_duplicate_ppr_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/word_tolerated_broken_media_rel_word_tolerated_duplicate_ppr_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/word_tolerated_duplicate_ppr_word_tolerated_misplaced_link_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/word_tolerated_duplicate_ppr_word_tolerated_misplaced_link_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/word_tolerated_misplaced_link_word_tolerated_misplaced_pgsz_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/word_tolerated_misplaced_link_word_tolerated_misplaced_pgsz_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/word_tolerated_misplaced_pgsz_word_tolerated_misplaced_uipriority_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/word_tolerated_misplaced_pgsz_word_tolerated_misplaced_uipriority_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/word_tolerated_misplaced_uipriority_word_tolerated_orphan_comment_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/word_tolerated_misplaced_uipriority_word_tolerated_orphan_comment_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/word_tolerated_orphan_comment_yellow_highlight_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/word_tolerated_orphan_comment_yellow_highlight_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_accepted_word/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_100_file_101_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_100_file_101_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_101_file_102_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_101_file_102_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_102_file_103_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_102_file_103_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_103_file_104_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_103_file_104_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_104_file_105_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_104_file_105_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_105_file_106_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_105_file_106_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_106_file_107_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_106_file_107_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_107_file_108_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_107_file_108_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_108_file_109_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_108_file_109_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_109_file_110_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_109_file_110_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_10_file_11_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_10_file_11_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_110_file_111_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_110_file_111_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_111_file_112_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_111_file_112_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_112_file_113_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_112_file_113_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_113_file_114_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_113_file_114_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_114_file_115_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_114_file_115_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_115_file_116_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_115_file_116_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_116_file_117_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_116_file_117_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_117_file_118_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_117_file_118_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_118_file_119_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_118_file_119_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_119_file_120_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_119_file_120_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_11_file_12_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_11_file_12_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_120_file_121_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_120_file_121_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_121_file_122_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_121_file_122_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_122_file_123_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_122_file_123_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_123_file_124_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_123_file_124_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_124_file_125_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_124_file_125_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_125_file_126_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_125_file_126_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_126_file_127_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_126_file_127_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_127_file_128_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_127_file_128_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_128_file_129_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_128_file_129_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_129_file_130_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_129_file_130_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_12_file_13_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_12_file_13_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_130_file_131_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_130_file_131_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_131_file_132_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_131_file_132_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_132_file_133_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_132_file_133_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_133_file_134_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_133_file_134_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_134_file_135_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_134_file_135_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_135_file_136_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_135_file_136_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_136_file_137_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_136_file_137_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_137_file_138_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_137_file_138_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_138_file_139_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_138_file_139_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_139_file_140_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_139_file_140_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_13_file_14_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_13_file_14_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_140_file_141_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_140_file_141_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_141_file_142_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_141_file_142_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_142_file_143_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_142_file_143_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_143_file_144_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_143_file_144_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_144_file_145_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_144_file_145_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_145_file_146_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_145_file_146_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_146_file_147_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_146_file_147_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_147_file_148_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_147_file_148_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_148_file_149_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_148_file_149_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_149_file_150_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_149_file_150_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_14_file_15_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_14_file_15_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_150_file_151_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_150_file_151_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_151_file_152_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_151_file_152_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_152_file_153_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_152_file_153_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_153_file_154_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_153_file_154_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_154_file_155_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_154_file_155_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_155_file_156_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_155_file_156_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_156_file_157_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_156_file_157_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_157_file_158_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_157_file_158_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_158_file_159_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_158_file_159_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_159_file_160_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_159_file_160_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_15_file_16_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_15_file_16_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_160_file_161_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_160_file_161_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_161_file_162_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_161_file_162_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_162_file_163_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_162_file_163_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_163_file_164_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_163_file_164_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_164_file_165_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_164_file_165_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_165_file_166_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_165_file_166_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_166_file_167_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_166_file_167_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_167_file_168_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_167_file_168_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_168_file_169_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_168_file_169_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_169_file_170_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_169_file_170_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_16_file_17_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_16_file_17_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_170_file_171_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_170_file_171_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_171_file_172_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_171_file_172_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_172_file_173_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_172_file_173_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_173_file_174_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_173_file_174_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_174_file_175_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_174_file_175_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_175_file_176_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_175_file_176_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_176_file_177_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_176_file_177_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_177_file_178_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_177_file_178_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_178_file_179_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_178_file_179_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_179_file_180_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_179_file_180_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_17_file_18_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_17_file_18_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_180_file_181_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_180_file_181_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_181_file_182_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_181_file_182_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_182_file_183_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_182_file_183_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_183_file_184_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_183_file_184_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_184_file_185_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_184_file_185_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_185_file_186_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_185_file_186_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_186_file_187_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_186_file_187_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_187_file_188_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_187_file_188_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_188_file_189_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_188_file_189_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_189_file_190_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_189_file_190_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_18_file_19_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_18_file_19_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_190_file_191_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_190_file_191_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_191_file_192_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_191_file_192_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_192_file_193_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_192_file_193_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_193_file_194_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_193_file_194_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_194_file_195_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_194_file_195_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_195_file_196_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_195_file_196_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_196_file_197_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_196_file_197_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_197_file_198_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_197_file_198_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_198_file_199_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_198_file_199_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_19_file_20_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_19_file_20_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_1_file_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_1_file_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_20_file_21_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_20_file_21_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_21_file_22_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_21_file_22_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_22_file_23_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_22_file_23_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_23_file_24_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_23_file_24_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_24_file_25_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_24_file_25_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_25_file_26_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_25_file_26_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_26_file_27_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_26_file_27_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_27_file_28_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_27_file_28_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_28_file_29_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_28_file_29_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_29_file_30_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_29_file_30_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_2_file_3_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_2_file_3_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_30_file_31_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_30_file_31_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_31_file_32_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_31_file_32_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_32_file_33_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_32_file_33_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_33_file_34_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_33_file_34_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_34_file_35_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_34_file_35_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_35_file_36_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_35_file_36_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_36_file_37_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_36_file_37_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_37_file_38_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_37_file_38_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_38_file_39_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_38_file_39_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_39_file_40_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_39_file_40_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_3_file_4_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_3_file_4_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_40_file_41_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_40_file_41_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_41_file_42_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_41_file_42_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_42_file_43_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_42_file_43_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_43_file_44_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_43_file_44_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_44_file_45_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_44_file_45_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_45_file_46_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_45_file_46_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_46_file_47_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_46_file_47_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_49_file_50_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_49_file_50_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_4_file_5_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_4_file_5_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_50_file_51_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_50_file_51_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_51_file_52_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_51_file_52_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_52_file_53_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_52_file_53_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_53_file_54_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_53_file_54_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_54_file_55_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_54_file_55_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_55_file_56_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_55_file_56_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_56_file_57_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_56_file_57_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_57_file_58_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_57_file_58_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_58_file_59_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_58_file_59_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_59_file_60_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_59_file_60_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_5_file_6_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_5_file_6_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_60_file_61_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_60_file_61_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_61_file_62_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_61_file_62_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_62_file_63_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_62_file_63_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_63_file_64_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_63_file_64_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_64_file_65_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_64_file_65_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_65_file_66_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_65_file_66_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_66_file_67_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_66_file_67_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_67_file_68_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_67_file_68_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_68_file_69_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_68_file_69_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_69_file_70_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_69_file_70_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_6_file_7_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_6_file_7_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_70_file_71_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_70_file_71_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_71_file_72_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_71_file_72_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_72_file_73_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_72_file_73_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_73_file_74_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_73_file_74_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_74_file_75_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_74_file_75_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_75_file_76_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_75_file_76_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_76_file_77_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_76_file_77_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_77_file_78_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_77_file_78_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_78_file_79_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_78_file_79_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_79_file_80_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_79_file_80_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_7_file_8_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_7_file_8_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_80_file_81_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_80_file_81_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_81_file_82_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_81_file_82_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_82_file_83_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_82_file_83_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_83_file_84_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_83_file_84_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_84_file_85_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_84_file_85_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_85_file_86_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_85_file_86_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_86_file_87_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_86_file_87_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_87_file_88_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_87_file_88_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_88_file_89_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_88_file_89_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_89_file_90_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_89_file_90_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_8_file_9_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_8_file_9_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_90_file_91_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_90_file_91_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_91_file_92_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_91_file_92_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_92_file_93_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_92_file_93_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_93_file_94_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_93_file_94_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_94_file_95_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_94_file_95_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_95_file_96_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_95_file_96_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_96_file_97_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_96_file_97_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_97_file_98_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_97_file_98_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_98_file_99_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_98_file_99_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_99_file_100_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_99_file_100_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_9_file_10_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_randomized/file_9_file_10_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/1_5_line_spacing_id_paraid_overflow_24_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/1_5_line_spacing_id_paraid_overflow_24_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/24_id_paraid_overflow_alternate_content_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/24_id_paraid_overflow_alternate_content_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/24_id_paraid_overflow_blue_bold_centered_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/24_id_paraid_overflow_blue_bold_centered_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_increase_indent_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_increase_indent_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/alternate_content_anchor_images_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/alternate_content_anchor_images_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/blue_bold_centered_demo_id_paraid_overflow_blue_centered_title_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/blue_bold_centered_demo_id_paraid_overflow_blue_centered_title_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/blue_centered_title_demo_style_default_missing_blue_italic_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/blue_centered_title_demo_style_default_missing_blue_italic_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/blue_italic_text_demo_id_paraid_overflow_blue_underline_combo_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/blue_italic_text_demo_id_paraid_overflow_blue_underline_combo_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/blue_underline_combo_demo_id_paraid_overflow_bold_and_italic_combo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/blue_underline_combo_demo_id_paraid_overflow_bold_and_italic_combo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_and_italic_combo_style_default_missing_bold_and_underline_combo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_and_italic_combo_style_default_missing_bold_and_underline_combo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_and_underline_combo_id_paraid_overflow_bold_italic_combined_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_and_underline_combo_id_paraid_overflow_bold_italic_combined_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_italic_combined_demo_id_paraid_overflow_bold_italic_underline_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_italic_combined_demo_id_paraid_overflow_bold_italic_underline_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_italic_underline_demo_id_paraid_overflow_bold_red_text_combo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_italic_underline_demo_id_paraid_overflow_bold_red_text_combo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_red_text_combo_id_paraid_overflow_bold_superscript_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_red_text_combo_id_paraid_overflow_bold_superscript_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_superscript_demo_style_default_missing_bold_text_formatting_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_superscript_demo_style_default_missing_bold_text_formatting_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_text_formatting_demo_id_paraid_overflow_2_bold_text_formatting_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_text_formatting_demo_id_paraid_overflow_2_bold_text_formatting_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_text_formatting_demo_id_paraid_overflow_bold_underline_combined_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_text_formatting_demo_id_paraid_overflow_bold_underline_combined_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_underline_combined_demo_id_paraid_overflow_bold_underline_highlight_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_underline_combined_demo_id_paraid_overflow_bold_underline_highlight_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_underline_highlight_demo_id_paraid_overflow_book_catalog_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bold_underline_highlight_demo_id_paraid_overflow_book_catalog_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/book_catalog_id_paraid_overflow_book_catalog_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/book_catalog_id_paraid_overflow_book_catalog_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/book_catalog_table_budget_report_q1_2026_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/book_catalog_table_budget_report_q1_2026_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/book_catalog_table_budget_report_q1_2026_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/book_catalog_table_budget_report_q1_2026_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/budget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/budget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/budget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/budget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bullet_list_bold_demo_id_paraid_overflow_bullet_list_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bullet_list_bold_demo_id_paraid_overflow_bullet_list_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bullet_list_demo_id_paraid_overflow_calibri_bold_italic_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/bullet_list_demo_id_paraid_overflow_calibri_bold_italic_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/calibri_bold_italic_demo_id_paraid_overflow_calibri_font_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/calibri_bold_italic_demo_id_paraid_overflow_calibri_font_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/calibri_font_demo_id_paraid_overflow_2_calibri_font_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/calibri_font_demo_id_paraid_overflow_2_calibri_font_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/calibri_font_demo_id_paraid_overflow_calibri_heading_2_right_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/calibri_font_demo_id_paraid_overflow_calibri_heading_2_right_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/calibri_heading_2_right_id_paraid_overflow_center_aligned_bold_text_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/calibri_heading_2_right_id_paraid_overflow_center_aligned_bold_text_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/center_aligned_bold_text_id_paraid_overflow_center_alignment_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/center_aligned_bold_text_id_paraid_overflow_center_alignment_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/center_alignment_demo_id_paraid_overflow_2_center_alignment_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/center_alignment_demo_id_paraid_overflow_2_center_alignment_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/center_alignment_demo_id_paraid_overflow_center_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/center_alignment_demo_id_paraid_overflow_center_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/center_bold_demo_id_paraid_overflow_clear_formatting_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/center_bold_demo_id_paraid_overflow_clear_formatting_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/clear_formatting_demo_id_paraid_overflow_comments_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/clear_formatting_demo_id_paraid_overflow_comments_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/clear_formatting_demo_id_paraid_overflow_contract_review_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/clear_formatting_demo_id_paraid_overflow_contract_review_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/comments_complex_style_attr_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/comments_complex_style_attr_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/complex_style_attr_contract_review_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/complex_style_attr_contract_review_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/document_100_ultimate_demo_id_paraid_overflow_docx_lots_of_comments_addition_redline_addition_v_removal_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/document_100_ultimate_demo_id_paraid_overflow_docx_lots_of_comments_addition_redline_addition_v_removal_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/document_100_ultimate_demo_id_paraid_overflow_double_spacing_bold_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/document_100_ultimate_demo_id_paraid_overflow_double_spacing_bold_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/docx_lots_of_comments_addition_docx_lots_of_comments_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/docx_lots_of_comments_addition_docx_lots_of_comments_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/docx_lots_of_comments_addition_redline_addition_v_removal_docx_lots_of_comments_addition_redline_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/docx_lots_of_comments_addition_redline_addition_v_removal_docx_lots_of_comments_addition_redline_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/docx_lots_of_comments_addition_redline_docx_lots_of_comments_addition_removal_redline_removal_v_addition_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/docx_lots_of_comments_addition_redline_docx_lots_of_comments_addition_removal_redline_removal_v_addition_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/docx_lots_of_comments_addition_removal_docx_lots_of_comments_addition_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/docx_lots_of_comments_addition_removal_docx_lots_of_comments_addition_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/docx_lots_of_comments_addition_removal_redline_docx_lots_of_comments_addition_removal_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/docx_lots_of_comments_addition_removal_redline_docx_lots_of_comments_addition_removal_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/docx_lots_of_comments_addition_removal_redline_removal_v_addition_docx_lots_of_comments_addition_removal_redline_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/docx_lots_of_comments_addition_removal_redline_removal_v_addition_docx_lots_of_comments_addition_removal_redline_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/docx_lots_of_comments_double_spacing_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/docx_lots_of_comments_double_spacing_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/double_spacing_bold_demo_id_paraid_overflow_eigenpal_docx_editor_suggesting_mixed_edits_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/double_spacing_bold_demo_id_paraid_overflow_eigenpal_docx_editor_suggesting_mixed_edits_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/eigenpal_docx_editor_suggesting_mixed_edits_employee_directory_table_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/eigenpal_docx_editor_suggesting_mixed_edits_employee_directory_table_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/employee_directory_table_2_employee_directory_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/employee_directory_table_2_employee_directory_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/employee_directory_table_employee_review_john_smith_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/employee_directory_table_employee_review_john_smith_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/employee_directory_table_employee_review_john_smith_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/employee_directory_table_employee_review_john_smith_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/employee_review_john_smith_suggesting_insertions_font_color_blue_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/employee_review_john_smith_suggesting_insertions_font_color_blue_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_color_blue_demo_style_default_missing_font_color_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_color_blue_demo_style_default_missing_font_color_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_color_demo_style_default_missing_font_family_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_color_demo_style_default_missing_font_family_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_family_demo_id_paraid_overflow_font_size_12_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_family_demo_id_paraid_overflow_font_size_12_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_size_12_demo_id_paraid_overflow_font_size_18_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_size_12_demo_id_paraid_overflow_font_size_18_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_size_18_demo_style_default_missing_font_size_24_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_size_18_demo_style_default_missing_font_size_24_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_size_24_demo_id_paraid_overflow_font_size_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_size_24_demo_id_paraid_overflow_font_size_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_size_demo_id_paraid_overflow_footnotes_sample_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_size_demo_id_paraid_overflow_footnotes_sample_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_size_demo_id_paraid_overflow_green_bold_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/font_size_demo_id_paraid_overflow_green_bold_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/footnotes_sample_gdocs_comments_export_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/footnotes_sample_gdocs_comments_export_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/gdocs_comments_export_green_bold_text_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/gdocs_comments_export_green_bold_text_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/green_bold_text_demo_id_paraid_overflow_green_highlight_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/green_bold_text_demo_id_paraid_overflow_green_highlight_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/green_highlight_demo_id_paraid_overflow_green_underline_bullet_list_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/green_highlight_demo_id_paraid_overflow_green_underline_bullet_list_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/green_underline_bullet_list_id_paraid_overflow_header_no_rels_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/green_underline_bullet_list_id_paraid_overflow_header_no_rels_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/green_underline_bullet_list_id_paraid_overflow_heading_1_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/green_underline_bullet_list_id_paraid_overflow_heading_1_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/header_no_rels_heading_1_bold_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/header_no_rels_heading_1_bold_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_1_bold_demo_id_paraid_overflow_heading_1_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_1_bold_demo_id_paraid_overflow_heading_1_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_1_style_demo_id_paraid_overflow_heading_2_center_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_1_style_demo_id_paraid_overflow_heading_2_center_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_2_center_demo_id_paraid_overflow_heading_2_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_2_center_demo_id_paraid_overflow_heading_2_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_2_style_demo_id_paraid_overflow_heading_3_center_italic_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_2_style_demo_id_paraid_overflow_heading_3_center_italic_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_3_center_italic_id_paraid_overflow_heading_3_style_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_3_center_italic_id_paraid_overflow_heading_3_style_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_3_style_demo_id_paraid_overflow_2_heading_3_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_3_style_demo_id_paraid_overflow_2_heading_3_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_3_style_demo_id_paraid_overflow_heading_4_right_italic_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_3_style_demo_id_paraid_overflow_heading_4_right_italic_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_4_right_italic_id_paraid_overflow_heading_4_style_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_4_right_italic_id_paraid_overflow_heading_4_style_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_4_style_demo_id_paraid_overflow_2_heading_4_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_4_style_demo_id_paraid_overflow_2_heading_4_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_4_style_demo_id_paraid_overflow_helvetica_font_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/heading_4_style_demo_id_paraid_overflow_helvetica_font_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/helvetica_font_demo_style_default_missing_hr_onboarding_checklist_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/helvetica_font_demo_style_default_missing_hr_onboarding_checklist_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/hr_onboarding_checklist_table_I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/hr_onboarding_checklist_table_I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/increase_indent_demo_id_paraid_overflow_insert_link_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/increase_indent_demo_id_paraid_overflow_insert_link_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/italic_and_underline_combo_style_default_missing_italic_subscript_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/italic_and_underline_combo_style_default_missing_italic_subscript_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/italic_subscript_demo_style_default_missing_italic_text_formatting_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/italic_subscript_demo_style_default_missing_italic_text_formatting_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/italic_text_formatting_demo_id_paraid_overflow_2_italic_text_formatting_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/italic_text_formatting_demo_id_paraid_overflow_2_italic_text_formatting_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/italic_text_formatting_demo_id_paraid_overflow_italic_underline_combined_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/italic_text_formatting_demo_id_paraid_overflow_italic_underline_combined_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/italic_underline_combined_demo_id_paraid_overflow_justified_underline_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/italic_underline_combined_demo_id_paraid_overflow_justified_underline_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/justified_underline_demo_id_paraid_overflow_justify_alignment_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/justified_underline_demo_id_paraid_overflow_justify_alignment_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/justify_alignment_demo_id_paraid_overflow_2_justify_alignment_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/justify_alignment_demo_id_paraid_overflow_2_justify_alignment_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/justify_alignment_demo_id_paraid_overflow_large_font_size_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/justify_alignment_demo_id_paraid_overflow_large_font_size_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/large_font_size_demo_id_paraid_overflow_left_alignment_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/large_font_size_demo_id_paraid_overflow_left_alignment_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/left_alignment_demo_id_paraid_overflow_line_spacing_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/left_alignment_demo_id_paraid_overflow_line_spacing_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/marketing_strategy_2026_suggesting_insertions_meeting_agenda_table_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/marketing_strategy_2026_suggesting_insertions_meeting_agenda_table_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/mcdoc_meeting_agenda_table_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/mcdoc_meeting_agenda_table_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/meeting_agenda_table_2_meeting_agenda_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/meeting_agenda_table_2_meeting_agenda_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/meeting_agenda_table_meeting_minutes_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/meeting_agenda_table_meeting_minutes_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/meeting_minutes_suggesting_insertions_multi_section_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/meeting_minutes_suggesting_insertions_multi_section_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/meeting_minutes_suggesting_insertions_numbered_list_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/meeting_minutes_suggesting_insertions_numbered_list_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/multi_section_nested_table_rowspan_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/multi_section_nested_table_rowspan_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/nested_table_rowspan_numbered_list_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/nested_table_rowspan_numbered_list_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/numbered_list_demo_id_paraid_overflow_numbered_list_italic_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/numbered_list_demo_id_paraid_overflow_numbered_list_italic_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/numbered_list_italic_demo_id_paraid_overflow_numwords_fldsimple_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/numbered_list_italic_demo_id_paraid_overflow_numwords_fldsimple_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/numbered_list_italic_demo_id_paraid_overflow_open_sans_bold_underline_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/numbered_list_italic_demo_id_paraid_overflow_open_sans_bold_underline_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/numwords_fldsimple_ole_object_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/numwords_fldsimple_ole_object_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/ole_object_ooxml_style_link_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/ole_object_ooxml_style_link_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/ooxml_style_link_open_sans_bold_underline_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/ooxml_style_link_open_sans_bold_underline_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/open_sans_bold_underline_id_paraid_overflow_open_sans_font_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/open_sans_bold_underline_id_paraid_overflow_open_sans_font_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/open_sans_font_demo_id_paraid_overflow_2_open_sans_font_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/open_sans_font_demo_id_paraid_overflow_2_open_sans_font_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/open_sans_font_demo_id_paraid_overflow_page_numbering_examples_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/open_sans_font_demo_id_paraid_overflow_page_numbering_examples_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/open_sans_font_demo_id_paraid_overflow_product_roadmap_2026_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/open_sans_font_demo_id_paraid_overflow_product_roadmap_2026_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/page_numbering_examples_potpourritest_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/page_numbering_examples_potpourritest_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/potpourritest_product_roadmap_2026_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/potpourritest_product_roadmap_2026_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_proposal_id_paraid_overflow_project_proposal_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_proposal_id_paraid_overflow_project_proposal_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_tasks_suggesting_insertions_q1_sales_summary_table_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_tasks_suggesting_insertions_q1_sales_summary_table_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_tasks_suggesting_insertions_q1_sales_summary_table_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/project_tasks_suggesting_insertions_q1_sales_summary_table_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/q1_sales_summary_table_2_q1_sales_summary_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/q1_sales_summary_table_2_q1_sales_summary_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/q1_sales_summary_table_quarterly_performance_report_table_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/q1_sales_summary_table_quarterly_performance_report_table_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/quarterly_performance_report_table_2_quarterly_performance_report_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/quarterly_performance_report_table_2_quarterly_performance_report_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/quarterly_performance_report_table_red_bold_heading_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/quarterly_performance_report_table_red_bold_heading_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/red_bold_heading_demo_style_default_missing_red_bold_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/red_bold_heading_demo_style_default_missing_red_bold_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/red_bold_text_demo_id_paraid_overflow_red_heading_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/red_bold_text_demo_id_paraid_overflow_red_heading_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/red_heading_demo_id_paraid_overflow_red_strikethrough_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/red_heading_demo_id_paraid_overflow_red_strikethrough_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/red_strikethrough_demo_style_default_missing_redline_cicerodo_v_plate_30_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/red_strikethrough_demo_style_default_missing_redline_cicerodo_v_plate_30_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/red_strikethrough_demo_style_default_missing_right_align_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/red_strikethrough_demo_style_default_missing_right_align_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/redline_cicerodo_v_plate_30_right_align_bold_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/redline_cicerodo_v_plate_30_right_align_bold_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/right_align_bold_demo_id_paraid_overflow_right_aligned_italic_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/right_align_bold_demo_id_paraid_overflow_right_aligned_italic_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/right_aligned_italic_demo_id_paraid_overflow_right_alignment_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/right_aligned_italic_demo_id_paraid_overflow_right_alignment_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/right_alignment_demo_id_paraid_overflow_2_right_alignment_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/right_alignment_demo_id_paraid_overflow_2_right_alignment_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/roboto_font_demo_id_paraid_overflow_2_roboto_font_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/roboto_font_demo_id_paraid_overflow_2_roboto_font_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/roboto_font_demo_id_paraid_overflow_roboto_underline_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/roboto_font_demo_id_paraid_overflow_roboto_underline_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sample_document_afterword_repaired_word_repaired_sample_document_really_repaired_word_repaired_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sample_document_afterword_repaired_word_repaired_sample_document_really_repaired_word_repaired_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sample_document_really_repaired_word_repaired_sample_document_word_repair_of_our_output_iter2_word_repaired_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sample_document_really_repaired_word_repaired_sample_document_word_repair_of_our_output_iter2_word_repaired_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sample_document_word_repair_of_our_output_word_repaired_sd_2517_localized_heading_styles_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sample_document_word_repair_of_our_output_word_repaired_sd_2517_localized_heading_styles_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sample_document_word_repair_of_our_output_word_repaired_small_font_size_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sample_document_word_repair_of_our_output_word_repaired_small_font_size_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sd_2517_localized_heading_styles_sectpr_headerref_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sd_2517_localized_heading_styles_sectpr_headerref_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sectpr_headerref_single_paragraph_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/sectpr_headerref_single_paragraph_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/single_paragraph_small_font_size_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/single_paragraph_small_font_size_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/small_font_size_demo_id_paraid_overflow_strict01_sdt_controls_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/small_font_size_demo_id_paraid_overflow_strict01_sdt_controls_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/small_font_size_demo_id_paraid_overflow_strikethrough_and_italic_combo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/small_font_size_demo_id_paraid_overflow_strikethrough_and_italic_combo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/strict01_sdt_controls_strict01_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/strict01_sdt_controls_strict01_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/strict01_strikethrough_and_italic_combo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/strict01_strikethrough_and_italic_combo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/strikethrough_and_italic_combo_id_paraid_overflow_strikethrough_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/strikethrough_and_italic_combo_id_paraid_overflow_strikethrough_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/strikethrough_bold_demo_id_paraid_overflow_strikethrough_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/strikethrough_bold_demo_id_paraid_overflow_strikethrough_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/strikethrough_text_demo_id_paraid_overflow_strikethrough_text_formatting_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/strikethrough_text_demo_id_paraid_overflow_strikethrough_text_formatting_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/strikethrough_text_formatting_demo_id_paraid_overflow_subscript_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/strikethrough_text_formatting_demo_id_paraid_overflow_subscript_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/subscript_demo_id_paraid_overflow_subscript_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/subscript_demo_id_paraid_overflow_subscript_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/subscript_demo_style_default_missing_subtitle_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/subscript_demo_style_default_missing_subtitle_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/subtitle_style_demo_id_paraid_overflow_subtitle_style_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/subtitle_style_demo_id_paraid_overflow_subtitle_style_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/subtitle_style_demo_style_default_missing_superscript_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/subtitle_style_demo_style_default_missing_superscript_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/superscript_demo_id_paraid_overflow_2_superscript_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/superscript_demo_id_paraid_overflow_2_superscript_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/superscript_demo_id_paraid_overflow_superscript_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/superscript_demo_id_paraid_overflow_superscript_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/superscript_demo_style_default_missing_support_tickets_summary_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/superscript_demo_style_default_missing_support_tickets_summary_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/superscript_demo_style_default_missing_support_tickets_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/superscript_demo_style_default_missing_support_tickets_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/support_tickets_summary_id_paraid_overflow_support_tickets_table_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/support_tickets_summary_id_paraid_overflow_support_tickets_table_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/support_tickets_summary_id_paraid_overflow_text_highlight_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/support_tickets_summary_id_paraid_overflow_text_highlight_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/support_tickets_table_support_tickets_summary_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/support_tickets_table_support_tickets_summary_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/support_tickets_table_table_bookmark_end_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/support_tickets_table_table_bookmark_end_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/table_bookmark_end_table_vmerge_colspan_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/table_bookmark_end_table_vmerge_colspan_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/table_vmerge_colspan_text_box_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/table_vmerge_colspan_text_box_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/text_box_text_highlight_demo_style_default_missing_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/text_box_text_highlight_demo_style_default_missing_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/text_highlight_demo_style_default_missing_tiff_image_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/text_highlight_demo_style_default_missing_tiff_image_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/text_highlight_demo_style_default_missing_times_new_roman_bold_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/text_highlight_demo_style_default_missing_times_new_roman_bold_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/tiff_image_times_new_roman_bold_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/tiff_image_times_new_roman_bold_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/times_new_roman_bold_id_paraid_overflow_times_new_roman_font_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/times_new_roman_bold_id_paraid_overflow_times_new_roman_font_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/times_new_roman_font_id_paraid_overflow_title_style_centered_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/times_new_roman_font_id_paraid_overflow_title_style_centered_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/title_style_centered_demo_id_paraid_overflow_title_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/title_style_centered_demo_id_paraid_overflow_title_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/title_style_demo_id_paraid_overflow_title_style_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/title_style_demo_id_paraid_overflow_title_style_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/title_style_demo_style_default_missing_track_changes_editing_bullet_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/title_style_demo_style_default_missing_track_changes_editing_bullet_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_editing_bullet_id_paraid_overflow_track_changes_editing_strikethrough_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_editing_bullet_id_paraid_overflow_track_changes_editing_strikethrough_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_editing_strikethrough_id_paraid_overflow_track_changes_suggesting_bold_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_editing_strikethrough_id_paraid_overflow_track_changes_suggesting_bold_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_suggesting_bold_id_paraid_overflow_track_changes_suggesting_calibri_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_suggesting_bold_id_paraid_overflow_track_changes_suggesting_calibri_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_suggesting_calibri_id_paraid_overflow_track_changes_suggesting_center_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_suggesting_calibri_id_paraid_overflow_track_changes_suggesting_center_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_suggesting_center_id_paraid_overflow_track_changes_suggesting_heading_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_suggesting_center_id_paraid_overflow_track_changes_suggesting_heading_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_suggesting_heading_id_paraid_overflow_track_changes_suggesting_italic_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_suggesting_heading_id_paraid_overflow_track_changes_suggesting_italic_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_suggesting_italic_id_paraid_overflow_track_changes_suggesting_title_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_suggesting_italic_id_paraid_overflow_track_changes_suggesting_title_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/underline_text_demo_id_paraid_overflow_underline_text_formatting_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/underline_text_demo_id_paraid_overflow_underline_text_formatting_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/underline_text_formatting_demo_style_default_missing_verdana_bold_large_font_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/underline_text_formatting_demo_style_default_missing_verdana_bold_large_font_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/verdana_font_demo_id_paraid_overflow_2_verdana_font_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/verdana_font_demo_id_paraid_overflow_2_verdana_font_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/verdana_font_demo_id_paraid_overflow_verdana_italic_centered_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/verdana_font_demo_id_paraid_overflow_verdana_italic_centered_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/verdana_italic_centered_demo_id_paraid_overflow_vfdsdfcacawesd_suggesting_mixed_edits_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/verdana_italic_centered_demo_id_paraid_overflow_vfdsdfcacawesd_suggesting_mixed_edits_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/verdana_italic_centered_demo_id_paraid_overflow_word_clean_strict01_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/verdana_italic_centered_demo_id_paraid_overflow_word_clean_strict01_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/vfdsdfcacawesd_suggesting_mixed_edits_yellow_highlight_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/vfdsdfcacawesd_suggesting_mixed_edits_yellow_highlight_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/word_clean_strict01_word_tolerated_broken_media_rel_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/word_clean_strict01_word_tolerated_broken_media_rel_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/word_tolerated_broken_media_rel_word_tolerated_duplicate_ppr_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/word_tolerated_broken_media_rel_word_tolerated_duplicate_ppr_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/word_tolerated_duplicate_ppr_word_tolerated_misplaced_link_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/word_tolerated_duplicate_ppr_word_tolerated_misplaced_link_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/word_tolerated_misplaced_link_word_tolerated_misplaced_pgsz_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/word_tolerated_misplaced_link_word_tolerated_misplaced_pgsz_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/word_tolerated_misplaced_pgsz_word_tolerated_misplaced_uipriority_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/word_tolerated_misplaced_pgsz_word_tolerated_misplaced_uipriority_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/word_tolerated_misplaced_uipriority_word_tolerated_orphan_comment_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/word_tolerated_misplaced_uipriority_word_tolerated_orphan_comment_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/word_tolerated_orphan_comment_yellow_highlight_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/word_tolerated_orphan_comment_yellow_highlight_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_redlines_word/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/1_5_line_spacing_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/1_5_line_spacing_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/24_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/24_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/Redline_CiceroDo_v_plate_30.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/Redline_CiceroDo_v_plate_30.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/Strict01.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/Strict01.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/alternate_content.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/alternate_content.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/anchor_images.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/anchor_images.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/blue_bold_centered_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/blue_bold_centered_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/blue_centered_title_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/blue_centered_title_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/blue_italic_text_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/blue_italic_text_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/blue_underline_combo_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/blue_underline_combo_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_and_italic_combo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_and_italic_combo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_and_underline_combo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_and_underline_combo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_italic_combined_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_italic_combined_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_italic_underline_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_italic_underline_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_red_text_combo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_red_text_combo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_superscript_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_superscript_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_text_formatting_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_text_formatting_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_text_formatting_demo_id_paraid_overflow_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_text_formatting_demo_id_paraid_overflow_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_underline_combined_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_underline_combined_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_underline_highlight_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bold_underline_highlight_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/book_catalog_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/book_catalog_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/book_catalog_table.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/book_catalog_table.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/budget_report_q1_2026_suggesting_insertions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/budget_report_q1_2026_suggesting_insertions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bullet_list_bold_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bullet_list_bold_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bullet_list_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/bullet_list_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/calibri_bold_italic_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/calibri_bold_italic_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/calibri_font_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/calibri_font_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/calibri_font_demo_id_paraid_overflow_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/calibri_font_demo_id_paraid_overflow_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/calibri_heading_2_right_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/calibri_heading_2_right_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/center_aligned_bold_text_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/center_aligned_bold_text_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/center_alignment_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/center_alignment_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/center_alignment_demo_id_paraid_overflow_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/center_alignment_demo_id_paraid_overflow_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/center_bold_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/center_bold_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/clear_formatting_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/clear_formatting_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/comments.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/comments.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/complex_style_attr.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/complex_style_attr.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/contract_review_suggesting_insertions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/contract_review_suggesting_insertions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/contract_review_suggesting_mixed_edits.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/contract_review_suggesting_mixed_edits.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/customer_satisfaction_survey_q4_suggesting_insertions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/customer_satisfaction_survey_q4_suggesting_insertions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/document_100_ultimate_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/document_100_ultimate_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/docx_lots_of_comments.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/docx_lots_of_comments.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/docx_lots_of_comments_addition.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/docx_lots_of_comments_addition.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/docx_lots_of_comments_addition_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/docx_lots_of_comments_addition_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/docx_lots_of_comments_addition_redline_addition_v_removal.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/docx_lots_of_comments_addition_redline_addition_v_removal.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/docx_lots_of_comments_addition_removal.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/docx_lots_of_comments_addition_removal.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/docx_lots_of_comments_addition_removal_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/docx_lots_of_comments_addition_removal_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/docx_lots_of_comments_addition_removal_redline_removal_v_addition.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/docx_lots_of_comments_addition_removal_redline_removal_v_addition.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/double_spacing_bold_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/double_spacing_bold_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/eigenpal_docx_editor_suggesting_mixed_edits.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/eigenpal_docx_editor_suggesting_mixed_edits.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/eigenpal_docx_editor_suggesting_mixed_edits_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/eigenpal_docx_editor_suggesting_mixed_edits_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/employee_directory_table.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/employee_directory_table.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/employee_directory_table_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/employee_directory_table_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/employee_review_john_smith_suggesting_insertions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/employee_review_john_smith_suggesting_insertions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/endnotes_sample.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/endnotes_sample.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/font_color_blue_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/font_color_blue_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/font_color_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/font_color_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/font_family_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/font_family_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/font_size_12_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/font_size_12_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/font_size_18_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/font_size_18_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/font_size_24_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/font_size_24_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/font_size_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/font_size_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/footnotes_sample.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/footnotes_sample.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/gdocs_comments_export.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/gdocs_comments_export.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/green_bold_text_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/green_bold_text_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/green_highlight_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/green_highlight_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/green_underline_bullet_list_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/green_underline_bullet_list_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/header_no_rels.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/header_no_rels.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_1_bold_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_1_bold_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_1_style_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_1_style_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_2_center_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_2_center_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_2_style_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_2_style_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_3_center_italic_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_3_center_italic_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_3_style_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_3_style_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_3_style_demo_id_paraid_overflow_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_3_style_demo_id_paraid_overflow_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_4_right_italic_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_4_right_italic_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_4_style_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_4_style_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_4_style_demo_id_paraid_overflow_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/heading_4_style_demo_id_paraid_overflow_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/helvetica_font_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/helvetica_font_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/hr_onboarding_checklist_table.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/hr_onboarding_checklist_table.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/image_out_of_folder.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/image_out_of_folder.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/increase_indent_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/increase_indent_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/insert_link_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/insert_link_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/inventory_list_suggesting_deletions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/inventory_list_suggesting_deletions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/inventory_list_suggesting_mixed_edits.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/inventory_list_suggesting_mixed_edits.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/it_security_policy_v2_suggesting_insertions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/it_security_policy_v2_suggesting_insertions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/italic_and_underline_combo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/italic_and_underline_combo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/italic_subscript_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/italic_subscript_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/italic_text_formatting_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/italic_text_formatting_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/italic_text_formatting_demo_id_paraid_overflow_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/italic_text_formatting_demo_id_paraid_overflow_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/italic_underline_combined_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/italic_underline_combined_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/justified_underline_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/justified_underline_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/justify_alignment_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/justify_alignment_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/justify_alignment_demo_id_paraid_overflow_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/justify_alignment_demo_id_paraid_overflow_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/large_font_size_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/large_font_size_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/left_alignment_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/left_alignment_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/line_spacing_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/line_spacing_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/marketing_strategy_2026_suggesting_insertions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/marketing_strategy_2026_suggesting_insertions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/mcdoc.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/mcdoc.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/meeting_agenda_table.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/meeting_agenda_table.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/meeting_agenda_table_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/meeting_agenda_table_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/meeting_minutes_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/meeting_minutes_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/meeting_minutes_suggesting_insertions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/meeting_minutes_suggesting_insertions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/multi_section.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/multi_section.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/nested_table_rowspan.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/nested_table_rowspan.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/numbered_list_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/numbered_list_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/numbered_list_italic_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/numbered_list_italic_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/numwords_fldsimple.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/numwords_fldsimple.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/ole_object.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/ole_object.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/ooxml_style_link.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/ooxml_style_link.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/open_sans_bold_underline_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/open_sans_bold_underline_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/open_sans_font_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/open_sans_font_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/open_sans_font_demo_id_paraid_overflow_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/open_sans_font_demo_id_paraid_overflow_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/page_numbering_examples.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/page_numbering_examples.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/potpourritest.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/potpourritest.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/product_roadmap_2026_suggesting_insertions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/product_roadmap_2026_suggesting_insertions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/project_plan_suggesting_insertions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/project_plan_suggesting_insertions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/project_proposal_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/project_proposal_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/project_proposal_suggesting_insertions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/project_proposal_suggesting_insertions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/project_tasks_suggesting_insertions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/project_tasks_suggesting_insertions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/project_tasks_suggesting_insertions_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/project_tasks_suggesting_insertions_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/q1_sales_summary_table.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/q1_sales_summary_table.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/q1_sales_summary_table_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/q1_sales_summary_table_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/quarterly_performance_report_table.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/quarterly_performance_report_table.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/quarterly_performance_report_table_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/quarterly_performance_report_table_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/red_bold_heading_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/red_bold_heading_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/red_bold_text_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/red_bold_text_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/red_heading_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/red_heading_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/red_strikethrough_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/red_strikethrough_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/right_align_bold_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/right_align_bold_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/right_aligned_italic_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/right_aligned_italic_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/right_alignment_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/right_alignment_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/right_alignment_demo_id_paraid_overflow_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/right_alignment_demo_id_paraid_overflow_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/risk_assessment_product_launch_suggesting_insertions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/risk_assessment_product_launch_suggesting_insertions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/roboto_font_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/roboto_font_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/roboto_font_demo_id_paraid_overflow_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/roboto_font_demo_id_paraid_overflow_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/roboto_underline_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/roboto_underline_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sales_report_january_2026_suggesting_insertions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sales_report_january_2026_suggesting_insertions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sample_document_afterword_repaired_word_repaired.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sample_document_afterword_repaired_word_repaired.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sample_document_really_repaired_word_repaired.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sample_document_really_repaired_word_repaired.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sample_document_word_repair_of_our_output_iter2_word_repaired.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sample_document_word_repair_of_our_output_iter2_word_repaired.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sample_document_word_repair_of_our_output_iter2_word_repaired_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sample_document_word_repair_of_our_output_iter2_word_repaired_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sample_document_word_repair_of_our_output_word_repaired.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sample_document_word_repair_of_our_output_word_repaired.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sample_document_word_repair_of_our_output_word_repaired_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sample_document_word_repair_of_our_output_word_repaired_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sd_2517_localized_heading_styles.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sd_2517_localized_heading_styles.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sectpr_headerref.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/sectpr_headerref.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/single_paragraph.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/single_paragraph.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/small_font_size_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/small_font_size_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/strict01_sdt_controls.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/strict01_sdt_controls.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/strikethrough_and_italic_combo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/strikethrough_and_italic_combo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/strikethrough_bold_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/strikethrough_bold_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/strikethrough_text_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/strikethrough_text_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/strikethrough_text_formatting_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/strikethrough_text_formatting_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/subscript_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/subscript_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/subscript_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/subscript_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/subtitle_style_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/subtitle_style_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/subtitle_style_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/subtitle_style_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/superscript_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/superscript_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/superscript_demo_id_paraid_overflow_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/superscript_demo_id_paraid_overflow_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/superscript_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/superscript_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/support_tickets_summary_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/support_tickets_summary_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/support_tickets_table.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/support_tickets_table.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/table_bookmark_end.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/table_bookmark_end.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/table_vmerge_colspan.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/table_vmerge_colspan.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/text_box.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/text_box.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/text_highlight_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/text_highlight_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/tiff_image.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/tiff_image.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/times_new_roman_bold_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/times_new_roman_bold_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/times_new_roman_font_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/times_new_roman_font_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/title_style_centered_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/title_style_centered_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/title_style_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/title_style_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/title_style_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/title_style_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_editing_bullet_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_editing_bullet_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_editing_strikethrough_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_editing_strikethrough_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_suggesting_bold_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_suggesting_bold_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_suggesting_calibri_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_suggesting_calibri_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_suggesting_center_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_suggesting_center_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_suggesting_heading_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_suggesting_heading_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_suggesting_italic_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_suggesting_italic_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_suggesting_title_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/track_changes_suggesting_title_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/training_materials_onboarding_program_suggesting_insertions.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/training_materials_onboarding_program_suggesting_insertions.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/underline_text_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/underline_text_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/underline_text_formatting_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/underline_text_formatting_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/verdana_bold_large_font_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/verdana_bold_large_font_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/verdana_font_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/verdana_font_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/verdana_font_demo_id_paraid_overflow_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/verdana_font_demo_id_paraid_overflow_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/verdana_italic_centered_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/verdana_italic_centered_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/verdana_italic_centered_demo_id_paraid_overflow_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/verdana_italic_centered_demo_id_paraid_overflow_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/vfdsdfcacawesd_suggesting_mixed_edits.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/vfdsdfcacawesd_suggesting_mixed_edits.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/word_clean_strict01.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/word_clean_strict01.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/word_tolerated_broken_media_rel.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/word_tolerated_broken_media_rel.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/word_tolerated_duplicate_ppr.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/word_tolerated_duplicate_ppr.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/word_tolerated_misplaced_link.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/word_tolerated_misplaced_link.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/word_tolerated_misplaced_pgsz.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/word_tolerated_misplaced_pgsz.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/word_tolerated_misplaced_uipriority.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/word_tolerated_misplaced_uipriority.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/word_tolerated_orphan_comment.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/word_tolerated_orphan_comment.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/yellow_highlight_demo_id_paraid_overflow.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/yellow_highlight_demo_id_paraid_overflow.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/yellow_highlight_italic_demo_style_default_missing.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/yellow_highlight_italic_demo_style_default_missing.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/yellow_highlight_italic_demo_style_default_missing_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source/yellow_highlight_italic_demo_style_default_missing_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_1.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_1.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_10.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_10.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_100.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_100.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_101.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_101.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_102.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_102.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_103.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_103.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_104.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_104.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_105.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_105.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_106.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_106.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_107.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_107.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_108.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_108.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_109.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_109.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_11.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_11.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_110.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_110.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_111.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_111.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_112.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_112.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_113.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_113.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_114.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_114.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_115.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_115.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_116.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_116.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_117.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_117.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_118.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_118.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_119.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_119.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_12.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_12.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_120.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_120.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_121.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_121.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_122.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_122.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_123.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_123.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_124.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_124.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_125.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_125.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_126.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_126.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_127.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_127.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_128.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_128.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_129.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_129.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_13.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_13.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_130.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_130.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_131.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_131.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_132.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_132.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_133.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_133.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_134.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_134.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_135.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_135.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_136.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_136.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_137.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_137.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_138.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_138.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_139.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_139.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_14.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_14.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_140.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_140.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_141.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_141.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_142.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_142.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_143.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_143.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_144.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_144.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_145.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_145.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_146.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_146.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_147.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_147.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_148.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_148.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_149.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_149.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_15.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_15.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_150.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_150.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_151.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_151.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_152.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_152.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_153.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_153.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_154.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_154.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_155.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_155.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_156.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_156.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_157.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_157.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_158.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_158.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_159.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_159.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_16.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_16.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_160.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_160.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_161.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_161.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_162.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_162.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_163.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_163.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_164.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_164.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_165.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_165.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_166.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_166.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_167.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_167.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_168.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_168.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_169.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_169.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_17.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_17.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_170.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_170.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_171.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_171.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_172.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_172.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_173.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_173.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_174.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_174.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_175.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_175.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_176.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_176.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_177.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_177.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_178.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_178.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_179.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_179.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_18.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_18.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_180.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_180.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_181.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_181.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_182.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_182.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_183.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_183.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_184.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_184.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_185.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_185.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_186.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_186.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_187.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_187.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_188.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_188.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_189.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_189.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_19.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_19.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_190.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_190.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_191.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_191.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_192.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_192.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_193.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_193.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_194.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_194.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_195.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_195.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_196.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_196.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_197.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_197.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_198.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_198.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_199.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_199.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_2.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_2.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_20.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_20.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_21.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_21.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_22.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_22.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_23.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_23.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_24.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_24.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_25.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_25.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_26.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_26.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_27.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_27.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_28.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_28.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_29.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_29.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_3.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_3.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_30.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_30.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_31.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_31.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_32.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_32.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_33.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_33.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_34.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_34.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_35.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_35.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_36.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_36.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_37.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_37.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_38.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_38.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_39.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_39.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_4.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_4.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_40.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_40.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_41.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_41.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_42.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_42.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_43.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_43.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_44.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_44.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_45.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_45.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_46.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_46.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_47.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_47.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_48.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_48.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_49.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_49.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_5.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_5.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_50.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_50.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_51.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_51.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_52.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_52.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_53.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_53.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_54.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_54.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_55.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_55.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_56.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_56.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_57.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_57.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_58.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_58.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_59.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_59.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_6.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_6.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_60.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_60.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_61.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_61.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_62.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_62.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_63.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_63.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_64.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_64.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_65.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_65.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_66.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_66.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_67.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_67.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_68.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_68.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_69.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_69.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_7.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_7.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_70.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_70.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_71.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_71.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_72.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_72.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_73.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_73.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_74.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_74.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_75.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_75.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_76.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_76.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_77.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_77.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_78.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_78.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_79.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_79.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_8.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_8.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_80.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_80.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_81.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_81.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_82.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_82.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_83.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_83.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_84.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_84.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_85.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_85.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_86.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_86.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_87.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_87.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_88.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_88.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_89.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_89.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_9.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_9.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_90.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_90.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_91.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_91.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_92.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_92.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_93.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_93.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_94.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_94.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_95.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_95.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_96.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_96.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_97.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_97.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_98.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_98.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_99.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/docx_source_randomized/file_99.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/1_5_line_spacing_id_paraid_overflow_24_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/1_5_line_spacing_id_paraid_overflow_24_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/24_id_paraid_overflow_alternate_content_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/24_id_paraid_overflow_alternate_content_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/alternate_content_anchor_images_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/alternate_content_anchor_images_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/blue_bold_centered_demo_id_paraid_overflow_blue_centered_title_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/blue_bold_centered_demo_id_paraid_overflow_blue_centered_title_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/blue_centered_title_demo_style_default_missing_blue_italic_text_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/blue_centered_title_demo_style_default_missing_blue_italic_text_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/blue_italic_text_demo_id_paraid_overflow_blue_underline_combo_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/blue_italic_text_demo_id_paraid_overflow_blue_underline_combo_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/blue_underline_combo_demo_id_paraid_overflow_bold_and_italic_combo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/blue_underline_combo_demo_id_paraid_overflow_bold_and_italic_combo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_and_italic_combo_style_default_missing_bold_and_underline_combo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_and_italic_combo_style_default_missing_bold_and_underline_combo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_and_underline_combo_id_paraid_overflow_bold_italic_combined_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_and_underline_combo_id_paraid_overflow_bold_italic_combined_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_italic_combined_demo_id_paraid_overflow_bold_italic_underline_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_italic_combined_demo_id_paraid_overflow_bold_italic_underline_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_italic_underline_demo_id_paraid_overflow_bold_red_text_combo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_italic_underline_demo_id_paraid_overflow_bold_red_text_combo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_red_text_combo_id_paraid_overflow_bold_superscript_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_red_text_combo_id_paraid_overflow_bold_superscript_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_superscript_demo_style_default_missing_bold_text_formatting_demo_id_paraid_overflow_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_superscript_demo_style_default_missing_bold_text_formatting_demo_id_paraid_overflow_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_text_formatting_demo_id_paraid_overflow_2_bold_text_formatting_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_text_formatting_demo_id_paraid_overflow_2_bold_text_formatting_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_text_formatting_demo_id_paraid_overflow_bold_underline_combined_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_text_formatting_demo_id_paraid_overflow_bold_underline_combined_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_underline_combined_demo_id_paraid_overflow_bold_underline_highlight_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_underline_combined_demo_id_paraid_overflow_bold_underline_highlight_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_underline_highlight_demo_id_paraid_overflow_book_catalog_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bold_underline_highlight_demo_id_paraid_overflow_book_catalog_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/book_catalog_id_paraid_overflow_book_catalog_table_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/book_catalog_id_paraid_overflow_book_catalog_table_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/book_catalog_table_budget_report_q1_2026_suggesting_insertions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/book_catalog_table_budget_report_q1_2026_suggesting_insertions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/budget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/budget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bullet_list_bold_demo_id_paraid_overflow_bullet_list_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bullet_list_bold_demo_id_paraid_overflow_bullet_list_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bullet_list_demo_id_paraid_overflow_calibri_bold_italic_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/bullet_list_demo_id_paraid_overflow_calibri_bold_italic_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/calibri_bold_italic_demo_id_paraid_overflow_calibri_font_demo_id_paraid_overflow_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/calibri_bold_italic_demo_id_paraid_overflow_calibri_font_demo_id_paraid_overflow_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/calibri_font_demo_id_paraid_overflow_2_calibri_font_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/calibri_font_demo_id_paraid_overflow_2_calibri_font_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/calibri_font_demo_id_paraid_overflow_calibri_heading_2_right_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/calibri_font_demo_id_paraid_overflow_calibri_heading_2_right_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/calibri_heading_2_right_id_paraid_overflow_center_aligned_bold_text_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/calibri_heading_2_right_id_paraid_overflow_center_aligned_bold_text_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/center_aligned_bold_text_id_paraid_overflow_center_alignment_demo_id_paraid_overflow_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/center_aligned_bold_text_id_paraid_overflow_center_alignment_demo_id_paraid_overflow_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/center_alignment_demo_id_paraid_overflow_2_center_alignment_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/center_alignment_demo_id_paraid_overflow_2_center_alignment_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/center_alignment_demo_id_paraid_overflow_center_bold_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/center_alignment_demo_id_paraid_overflow_center_bold_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/center_bold_demo_id_paraid_overflow_clear_formatting_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/center_bold_demo_id_paraid_overflow_clear_formatting_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/clear_formatting_demo_id_paraid_overflow_comments_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/clear_formatting_demo_id_paraid_overflow_comments_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/comments_complex_style_attr_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/comments_complex_style_attr_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/complex_style_attr_contract_review_suggesting_insertions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/complex_style_attr_contract_review_suggesting_insertions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/document_100_ultimate_demo_id_paraid_overflow_double_spacing_bold_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/document_100_ultimate_demo_id_paraid_overflow_double_spacing_bold_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/employee_directory_table_2_employee_directory_table_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/employee_directory_table_2_employee_directory_table_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/employee_directory_table_employee_review_john_smith_suggesting_insertions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/employee_directory_table_employee_review_john_smith_suggesting_insertions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/font_color_blue_demo_style_default_missing_font_color_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/font_color_blue_demo_style_default_missing_font_color_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/font_color_demo_style_default_missing_font_family_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/font_color_demo_style_default_missing_font_family_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/font_family_demo_id_paraid_overflow_font_size_12_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/font_family_demo_id_paraid_overflow_font_size_12_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/font_size_12_demo_id_paraid_overflow_font_size_18_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/font_size_12_demo_id_paraid_overflow_font_size_18_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/font_size_18_demo_style_default_missing_font_size_24_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/font_size_18_demo_style_default_missing_font_size_24_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/font_size_24_demo_id_paraid_overflow_font_size_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/font_size_24_demo_id_paraid_overflow_font_size_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/font_size_demo_id_paraid_overflow_footnotes_sample_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/font_size_demo_id_paraid_overflow_footnotes_sample_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/footnotes_sample_gdocs_comments_export_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/footnotes_sample_gdocs_comments_export_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/gdocs_comments_export_green_bold_text_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/gdocs_comments_export_green_bold_text_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/green_bold_text_demo_id_paraid_overflow_green_highlight_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/green_bold_text_demo_id_paraid_overflow_green_highlight_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/green_highlight_demo_id_paraid_overflow_green_underline_bullet_list_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/green_highlight_demo_id_paraid_overflow_green_underline_bullet_list_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/green_underline_bullet_list_id_paraid_overflow_header_no_rels_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/green_underline_bullet_list_id_paraid_overflow_header_no_rels_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/header_no_rels_heading_1_bold_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/header_no_rels_heading_1_bold_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_1_bold_demo_id_paraid_overflow_heading_1_style_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_1_bold_demo_id_paraid_overflow_heading_1_style_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_1_style_demo_id_paraid_overflow_heading_2_center_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_1_style_demo_id_paraid_overflow_heading_2_center_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_2_center_demo_id_paraid_overflow_heading_2_style_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_2_center_demo_id_paraid_overflow_heading_2_style_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_2_style_demo_id_paraid_overflow_heading_3_center_italic_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_2_style_demo_id_paraid_overflow_heading_3_center_italic_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_3_center_italic_id_paraid_overflow_heading_3_style_demo_id_paraid_overflow_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_3_center_italic_id_paraid_overflow_heading_3_style_demo_id_paraid_overflow_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_3_style_demo_id_paraid_overflow_2_heading_3_style_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_3_style_demo_id_paraid_overflow_2_heading_3_style_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_3_style_demo_id_paraid_overflow_heading_4_right_italic_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_3_style_demo_id_paraid_overflow_heading_4_right_italic_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_4_right_italic_id_paraid_overflow_heading_4_style_demo_id_paraid_overflow_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_4_right_italic_id_paraid_overflow_heading_4_style_demo_id_paraid_overflow_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_4_style_demo_id_paraid_overflow_2_heading_4_style_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_4_style_demo_id_paraid_overflow_2_heading_4_style_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_4_style_demo_id_paraid_overflow_helvetica_font_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/heading_4_style_demo_id_paraid_overflow_helvetica_font_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/helvetica_font_demo_style_default_missing_hr_onboarding_checklist_table_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/helvetica_font_demo_style_default_missing_hr_onboarding_checklist_table_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/italic_and_underline_combo_style_default_missing_italic_subscript_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/italic_and_underline_combo_style_default_missing_italic_subscript_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/italic_subscript_demo_style_default_missing_italic_text_formatting_demo_id_paraid_overflow_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/italic_subscript_demo_style_default_missing_italic_text_formatting_demo_id_paraid_overflow_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/italic_text_formatting_demo_id_paraid_overflow_2_italic_text_formatting_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/italic_text_formatting_demo_id_paraid_overflow_2_italic_text_formatting_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/italic_text_formatting_demo_id_paraid_overflow_italic_underline_combined_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/italic_text_formatting_demo_id_paraid_overflow_italic_underline_combined_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/italic_underline_combined_demo_id_paraid_overflow_justified_underline_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/italic_underline_combined_demo_id_paraid_overflow_justified_underline_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/justified_underline_demo_id_paraid_overflow_justify_alignment_demo_id_paraid_overflow_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/justified_underline_demo_id_paraid_overflow_justify_alignment_demo_id_paraid_overflow_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/justify_alignment_demo_id_paraid_overflow_2_justify_alignment_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/justify_alignment_demo_id_paraid_overflow_2_justify_alignment_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/justify_alignment_demo_id_paraid_overflow_large_font_size_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/justify_alignment_demo_id_paraid_overflow_large_font_size_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/large_font_size_demo_id_paraid_overflow_left_alignment_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/large_font_size_demo_id_paraid_overflow_left_alignment_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/left_alignment_demo_id_paraid_overflow_line_spacing_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/left_alignment_demo_id_paraid_overflow_line_spacing_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/mcdoc_meeting_agenda_table_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/mcdoc_meeting_agenda_table_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/meeting_agenda_table_2_meeting_agenda_table_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/meeting_agenda_table_2_meeting_agenda_table_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/meeting_agenda_table_meeting_minutes_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/meeting_agenda_table_meeting_minutes_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/meeting_minutes_suggesting_insertions_multi_section_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/meeting_minutes_suggesting_insertions_multi_section_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/multi_section_nested_table_rowspan_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/multi_section_nested_table_rowspan_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/nested_table_rowspan_numbered_list_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/nested_table_rowspan_numbered_list_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/numbered_list_demo_id_paraid_overflow_numbered_list_italic_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/numbered_list_demo_id_paraid_overflow_numbered_list_italic_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/numbered_list_italic_demo_id_paraid_overflow_numwords_fldsimple_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/numbered_list_italic_demo_id_paraid_overflow_numwords_fldsimple_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/numwords_fldsimple_ole_object_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/numwords_fldsimple_ole_object_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/ole_object_ooxml_style_link_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/ole_object_ooxml_style_link_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/ooxml_style_link_open_sans_bold_underline_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/ooxml_style_link_open_sans_bold_underline_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/open_sans_bold_underline_id_paraid_overflow_open_sans_font_demo_id_paraid_overflow_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/open_sans_bold_underline_id_paraid_overflow_open_sans_font_demo_id_paraid_overflow_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/open_sans_font_demo_id_paraid_overflow_2_open_sans_font_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/open_sans_font_demo_id_paraid_overflow_2_open_sans_font_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/open_sans_font_demo_id_paraid_overflow_page_numbering_examples_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/open_sans_font_demo_id_paraid_overflow_page_numbering_examples_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/page_numbering_examples_potpourritest_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/page_numbering_examples_potpourritest_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/potpourritest_product_roadmap_2026_suggesting_insertions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/potpourritest_product_roadmap_2026_suggesting_insertions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/project_proposal_id_paraid_overflow_project_proposal_suggesting_insertions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/project_proposal_id_paraid_overflow_project_proposal_suggesting_insertions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/project_tasks_suggesting_insertions_q1_sales_summary_table_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/project_tasks_suggesting_insertions_q1_sales_summary_table_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/q1_sales_summary_table_2_q1_sales_summary_table_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/q1_sales_summary_table_2_q1_sales_summary_table_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/q1_sales_summary_table_quarterly_performance_report_table_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/q1_sales_summary_table_quarterly_performance_report_table_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/quarterly_performance_report_table_2_quarterly_performance_report_table_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/quarterly_performance_report_table_2_quarterly_performance_report_table_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/quarterly_performance_report_table_red_bold_heading_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/quarterly_performance_report_table_red_bold_heading_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/red_bold_heading_demo_style_default_missing_red_bold_text_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/red_bold_heading_demo_style_default_missing_red_bold_text_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/red_bold_text_demo_id_paraid_overflow_red_heading_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/red_bold_text_demo_id_paraid_overflow_red_heading_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/red_heading_demo_id_paraid_overflow_red_strikethrough_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/red_heading_demo_id_paraid_overflow_red_strikethrough_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/red_strikethrough_demo_style_default_missing_redline_cicerodo_v_plate_30_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/red_strikethrough_demo_style_default_missing_redline_cicerodo_v_plate_30_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/redline_cicerodo_v_plate_30_right_align_bold_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/redline_cicerodo_v_plate_30_right_align_bold_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/right_align_bold_demo_id_paraid_overflow_right_aligned_italic_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/right_align_bold_demo_id_paraid_overflow_right_aligned_italic_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/right_aligned_italic_demo_id_paraid_overflow_right_alignment_demo_id_paraid_overflow_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/right_aligned_italic_demo_id_paraid_overflow_right_alignment_demo_id_paraid_overflow_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/right_alignment_demo_id_paraid_overflow_2_right_alignment_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/right_alignment_demo_id_paraid_overflow_2_right_alignment_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/roboto_font_demo_id_paraid_overflow_2_roboto_font_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/roboto_font_demo_id_paraid_overflow_2_roboto_font_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/roboto_font_demo_id_paraid_overflow_roboto_underline_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/roboto_font_demo_id_paraid_overflow_roboto_underline_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/sample_document_word_repair_of_our_output_word_repaired_sd_2517_localized_heading_styles_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/sample_document_word_repair_of_our_output_word_repaired_sd_2517_localized_heading_styles_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/sd_2517_localized_heading_styles_sectpr_headerref_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/sd_2517_localized_heading_styles_sectpr_headerref_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/sectpr_headerref_single_paragraph_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/sectpr_headerref_single_paragraph_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/single_paragraph_small_font_size_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/single_paragraph_small_font_size_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/small_font_size_demo_id_paraid_overflow_strict01_sdt_controls_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/small_font_size_demo_id_paraid_overflow_strict01_sdt_controls_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/strict01_sdt_controls_strict01_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/strict01_sdt_controls_strict01_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/strict01_strikethrough_and_italic_combo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/strict01_strikethrough_and_italic_combo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/strikethrough_and_italic_combo_id_paraid_overflow_strikethrough_bold_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/strikethrough_and_italic_combo_id_paraid_overflow_strikethrough_bold_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/strikethrough_bold_demo_id_paraid_overflow_strikethrough_text_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/strikethrough_bold_demo_id_paraid_overflow_strikethrough_text_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/strikethrough_text_demo_id_paraid_overflow_strikethrough_text_formatting_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/strikethrough_text_demo_id_paraid_overflow_strikethrough_text_formatting_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/strikethrough_text_formatting_demo_id_paraid_overflow_subscript_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/strikethrough_text_formatting_demo_id_paraid_overflow_subscript_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/subscript_demo_id_paraid_overflow_subscript_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/subscript_demo_id_paraid_overflow_subscript_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/subscript_demo_style_default_missing_subtitle_style_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/subscript_demo_style_default_missing_subtitle_style_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/subtitle_style_demo_id_paraid_overflow_subtitle_style_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/subtitle_style_demo_id_paraid_overflow_subtitle_style_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/subtitle_style_demo_style_default_missing_superscript_demo_id_paraid_overflow_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/subtitle_style_demo_style_default_missing_superscript_demo_id_paraid_overflow_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/superscript_demo_id_paraid_overflow_2_superscript_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/superscript_demo_id_paraid_overflow_2_superscript_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/superscript_demo_id_paraid_overflow_superscript_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/superscript_demo_id_paraid_overflow_superscript_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/superscript_demo_style_default_missing_support_tickets_summary_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/superscript_demo_style_default_missing_support_tickets_summary_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/support_tickets_summary_id_paraid_overflow_support_tickets_table_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/support_tickets_summary_id_paraid_overflow_support_tickets_table_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/support_tickets_table_table_bookmark_end_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/support_tickets_table_table_bookmark_end_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/table_bookmark_end_table_vmerge_colspan_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/table_bookmark_end_table_vmerge_colspan_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/table_vmerge_colspan_text_box_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/table_vmerge_colspan_text_box_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/text_box_text_highlight_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/text_box_text_highlight_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/text_highlight_demo_style_default_missing_tiff_image_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/text_highlight_demo_style_default_missing_tiff_image_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/tiff_image_times_new_roman_bold_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/tiff_image_times_new_roman_bold_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/times_new_roman_bold_id_paraid_overflow_times_new_roman_font_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/times_new_roman_bold_id_paraid_overflow_times_new_roman_font_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/times_new_roman_font_id_paraid_overflow_title_style_centered_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/times_new_roman_font_id_paraid_overflow_title_style_centered_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/title_style_centered_demo_id_paraid_overflow_title_style_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/title_style_centered_demo_id_paraid_overflow_title_style_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/title_style_demo_id_paraid_overflow_title_style_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/title_style_demo_id_paraid_overflow_title_style_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/title_style_demo_style_default_missing_track_changes_editing_bullet_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/title_style_demo_style_default_missing_track_changes_editing_bullet_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_editing_bullet_id_paraid_overflow_track_changes_editing_strikethrough_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_editing_bullet_id_paraid_overflow_track_changes_editing_strikethrough_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_editing_strikethrough_id_paraid_overflow_track_changes_suggesting_bold_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_editing_strikethrough_id_paraid_overflow_track_changes_suggesting_bold_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_suggesting_bold_id_paraid_overflow_track_changes_suggesting_calibri_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_suggesting_bold_id_paraid_overflow_track_changes_suggesting_calibri_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_suggesting_calibri_id_paraid_overflow_track_changes_suggesting_center_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_suggesting_calibri_id_paraid_overflow_track_changes_suggesting_center_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_suggesting_center_id_paraid_overflow_track_changes_suggesting_heading_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_suggesting_center_id_paraid_overflow_track_changes_suggesting_heading_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_suggesting_heading_id_paraid_overflow_track_changes_suggesting_italic_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_suggesting_heading_id_paraid_overflow_track_changes_suggesting_italic_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_suggesting_italic_id_paraid_overflow_track_changes_suggesting_title_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_suggesting_italic_id_paraid_overflow_track_changes_suggesting_title_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/underline_text_demo_id_paraid_overflow_underline_text_formatting_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/underline_text_demo_id_paraid_overflow_underline_text_formatting_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_2_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_2_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/verdana_font_demo_id_paraid_overflow_2_verdana_font_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/verdana_font_demo_id_paraid_overflow_2_verdana_font_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/verdana_font_demo_id_paraid_overflow_verdana_italic_centered_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/verdana_font_demo_id_paraid_overflow_verdana_italic_centered_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/verdana_italic_centered_demo_id_paraid_overflow_vfdsdfcacawesd_suggesting_mixed_edits_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/verdana_italic_centered_demo_id_paraid_overflow_vfdsdfcacawesd_suggesting_mixed_edits_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/vfdsdfcacawesd_suggesting_mixed_edits_yellow_highlight_demo_id_paraid_overflow_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/vfdsdfcacawesd_suggesting_mixed_edits_yellow_highlight_demo_id_paraid_overflow_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_word_redline_accepted.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/corpus_sanity/word_based/word_working_roundtrip/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_word_redline_accepted.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  set displayAlerts to true
end tell