tell application "Microsoft Word"
  set displayAlerts to false
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/1_5_line_spacing_id_paraid_overflow_24_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/1_5_line_spacing_id_paraid_overflow_24_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/24_id_paraid_overflow_alternate_content_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/24_id_paraid_overflow_alternate_content_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/24_id_paraid_overflow_blue_bold_centered_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/24_id_paraid_overflow_blue_bold_centered_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_increase_indent_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_increase_indent_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/alternate_content_anchor_images_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/alternate_content_anchor_images_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/blue_bold_centered_demo_id_paraid_overflow_blue_centered_title_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/blue_bold_centered_demo_id_paraid_overflow_blue_centered_title_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/blue_centered_title_demo_style_default_missing_blue_italic_text_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/blue_centered_title_demo_style_default_missing_blue_italic_text_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/blue_italic_text_demo_id_paraid_overflow_blue_underline_combo_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/blue_italic_text_demo_id_paraid_overflow_blue_underline_combo_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/blue_underline_combo_demo_id_paraid_overflow_bold_and_italic_combo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/blue_underline_combo_demo_id_paraid_overflow_bold_and_italic_combo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/bold_and_italic_combo_style_default_missing_bold_and_underline_combo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/bold_and_italic_combo_style_default_missing_bold_and_underline_combo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/bold_and_underline_combo_id_paraid_overflow_bold_italic_combined_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/bold_and_underline_combo_id_paraid_overflow_bold_italic_combined_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/bold_italic_combined_demo_id_paraid_overflow_bold_italic_underline_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/bold_italic_combined_demo_id_paraid_overflow_bold_italic_underline_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/bold_italic_underline_demo_id_paraid_overflow_bold_red_text_combo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/bold_italic_underline_demo_id_paraid_overflow_bold_red_text_combo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/bold_red_text_combo_id_paraid_overflow_bold_superscript_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/bold_red_text_combo_id_paraid_overflow_bold_superscript_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/bold_superscript_demo_style_default_missing_bold_text_formatting_demo_id_paraid_overflow_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/bold_superscript_demo_style_default_missing_bold_text_formatting_demo_id_paraid_overflow_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/bold_text_formatting_demo_id_paraid_overflow_2_bold_text_formatting_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/bold_text_formatting_demo_id_paraid_overflow_2_bold_text_formatting_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/bold_text_formatting_demo_id_paraid_overflow_bold_underline_combined_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/bold_text_formatting_demo_id_paraid_overflow_bold_underline_combined_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/bold_underline_combined_demo_id_paraid_overflow_bold_underline_highlight_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/bold_underline_combined_demo_id_paraid_overflow_bold_underline_highlight_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/bold_underline_highlight_demo_id_paraid_overflow_book_catalog_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/bold_underline_highlight_demo_id_paraid_overflow_book_catalog_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/book_catalog_id_paraid_overflow_book_catalog_table_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/book_catalog_id_paraid_overflow_book_catalog_table_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/book_catalog_table_budget_report_q1_2026_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/book_catalog_table_budget_report_q1_2026_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/budget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/budget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/bullet_list_bold_demo_id_paraid_overflow_bullet_list_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/bullet_list_bold_demo_id_paraid_overflow_bullet_list_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/bullet_list_demo_id_paraid_overflow_calibri_bold_italic_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/bullet_list_demo_id_paraid_overflow_calibri_bold_italic_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/calibri_bold_italic_demo_id_paraid_overflow_calibri_font_demo_id_paraid_overflow_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/calibri_bold_italic_demo_id_paraid_overflow_calibri_font_demo_id_paraid_overflow_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/calibri_font_demo_id_paraid_overflow_2_calibri_font_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/calibri_font_demo_id_paraid_overflow_2_calibri_font_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/calibri_font_demo_id_paraid_overflow_calibri_heading_2_right_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/calibri_font_demo_id_paraid_overflow_calibri_heading_2_right_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/calibri_heading_2_right_id_paraid_overflow_center_aligned_bold_text_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/calibri_heading_2_right_id_paraid_overflow_center_aligned_bold_text_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/center_aligned_bold_text_id_paraid_overflow_center_alignment_demo_id_paraid_overflow_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/center_aligned_bold_text_id_paraid_overflow_center_alignment_demo_id_paraid_overflow_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/center_alignment_demo_id_paraid_overflow_2_center_alignment_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/center_alignment_demo_id_paraid_overflow_2_center_alignment_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/center_alignment_demo_id_paraid_overflow_center_bold_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/center_alignment_demo_id_paraid_overflow_center_bold_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/center_bold_demo_id_paraid_overflow_clear_formatting_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/center_bold_demo_id_paraid_overflow_clear_formatting_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/clear_formatting_demo_id_paraid_overflow_comments_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/clear_formatting_demo_id_paraid_overflow_comments_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/clear_formatting_demo_id_paraid_overflow_contract_review_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/clear_formatting_demo_id_paraid_overflow_contract_review_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/comments_complex_style_attr_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/comments_complex_style_attr_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/complex_style_attr_contract_review_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/complex_style_attr_contract_review_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/document_100_ultimate_demo_id_paraid_overflow_docx_lots_of_comments_addition_redline_addition_v_removal_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/document_100_ultimate_demo_id_paraid_overflow_docx_lots_of_comments_addition_redline_addition_v_removal_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/document_100_ultimate_demo_id_paraid_overflow_double_spacing_bold_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/document_100_ultimate_demo_id_paraid_overflow_double_spacing_bold_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/docx_lots_of_comments_addition_docx_lots_of_comments_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/docx_lots_of_comments_addition_docx_lots_of_comments_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/docx_lots_of_comments_addition_redline_addition_v_removal_docx_lots_of_comments_addition_redline_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/docx_lots_of_comments_addition_redline_addition_v_removal_docx_lots_of_comments_addition_redline_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/docx_lots_of_comments_addition_redline_docx_lots_of_comments_addition_removal_redline_removal_v_addition_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/docx_lots_of_comments_addition_redline_docx_lots_of_comments_addition_removal_redline_removal_v_addition_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/docx_lots_of_comments_addition_removal_docx_lots_of_comments_addition_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/docx_lots_of_comments_addition_removal_docx_lots_of_comments_addition_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/docx_lots_of_comments_addition_removal_redline_docx_lots_of_comments_addition_removal_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/docx_lots_of_comments_addition_removal_redline_docx_lots_of_comments_addition_removal_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/docx_lots_of_comments_addition_removal_redline_removal_v_addition_docx_lots_of_comments_addition_removal_redline_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/docx_lots_of_comments_addition_removal_redline_removal_v_addition_docx_lots_of_comments_addition_removal_redline_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/docx_lots_of_comments_double_spacing_bold_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/docx_lots_of_comments_double_spacing_bold_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/double_spacing_bold_demo_id_paraid_overflow_eigenpal_docx_editor_suggesting_mixed_edits_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/double_spacing_bold_demo_id_paraid_overflow_eigenpal_docx_editor_suggesting_mixed_edits_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/eigenpal_docx_editor_suggesting_mixed_edits_employee_directory_table_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/eigenpal_docx_editor_suggesting_mixed_edits_employee_directory_table_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/employee_directory_table_2_employee_directory_table_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/employee_directory_table_2_employee_directory_table_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/employee_directory_table_employee_review_john_smith_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/employee_directory_table_employee_review_john_smith_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/employee_review_john_smith_suggesting_insertions_font_color_blue_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/employee_review_john_smith_suggesting_insertions_font_color_blue_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/font_color_blue_demo_style_default_missing_font_color_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/font_color_blue_demo_style_default_missing_font_color_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/font_color_demo_style_default_missing_font_family_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/font_color_demo_style_default_missing_font_family_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/font_family_demo_id_paraid_overflow_font_size_12_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/font_family_demo_id_paraid_overflow_font_size_12_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/font_size_12_demo_id_paraid_overflow_font_size_18_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/font_size_12_demo_id_paraid_overflow_font_size_18_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/font_size_18_demo_style_default_missing_font_size_24_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/font_size_18_demo_style_default_missing_font_size_24_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/font_size_24_demo_id_paraid_overflow_font_size_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/font_size_24_demo_id_paraid_overflow_font_size_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/font_size_demo_id_paraid_overflow_footnotes_sample_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/font_size_demo_id_paraid_overflow_footnotes_sample_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/font_size_demo_id_paraid_overflow_green_bold_text_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/font_size_demo_id_paraid_overflow_green_bold_text_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/footnotes_sample_gdocs_comments_export_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/footnotes_sample_gdocs_comments_export_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/gdocs_comments_export_green_bold_text_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/gdocs_comments_export_green_bold_text_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/green_bold_text_demo_id_paraid_overflow_green_highlight_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/green_bold_text_demo_id_paraid_overflow_green_highlight_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/green_highlight_demo_id_paraid_overflow_green_underline_bullet_list_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/green_highlight_demo_id_paraid_overflow_green_underline_bullet_list_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/green_underline_bullet_list_id_paraid_overflow_header_no_rels_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/green_underline_bullet_list_id_paraid_overflow_header_no_rels_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/green_underline_bullet_list_id_paraid_overflow_heading_1_bold_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/green_underline_bullet_list_id_paraid_overflow_heading_1_bold_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/header_no_rels_heading_1_bold_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/header_no_rels_heading_1_bold_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/heading_1_bold_demo_id_paraid_overflow_heading_1_style_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/heading_1_bold_demo_id_paraid_overflow_heading_1_style_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/heading_1_style_demo_id_paraid_overflow_heading_2_center_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/heading_1_style_demo_id_paraid_overflow_heading_2_center_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/heading_2_center_demo_id_paraid_overflow_heading_2_style_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/heading_2_center_demo_id_paraid_overflow_heading_2_style_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/heading_2_style_demo_id_paraid_overflow_heading_3_center_italic_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/heading_2_style_demo_id_paraid_overflow_heading_3_center_italic_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/heading_3_center_italic_id_paraid_overflow_heading_3_style_demo_id_paraid_overflow_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/heading_3_center_italic_id_paraid_overflow_heading_3_style_demo_id_paraid_overflow_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/heading_3_style_demo_id_paraid_overflow_2_heading_3_style_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/heading_3_style_demo_id_paraid_overflow_2_heading_3_style_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/heading_3_style_demo_id_paraid_overflow_heading_4_right_italic_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/heading_3_style_demo_id_paraid_overflow_heading_4_right_italic_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/heading_4_right_italic_id_paraid_overflow_heading_4_style_demo_id_paraid_overflow_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/heading_4_right_italic_id_paraid_overflow_heading_4_style_demo_id_paraid_overflow_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/heading_4_style_demo_id_paraid_overflow_2_heading_4_style_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/heading_4_style_demo_id_paraid_overflow_2_heading_4_style_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/heading_4_style_demo_id_paraid_overflow_helvetica_font_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/heading_4_style_demo_id_paraid_overflow_helvetica_font_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/helvetica_font_demo_style_default_missing_hr_onboarding_checklist_table_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/helvetica_font_demo_style_default_missing_hr_onboarding_checklist_table_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/hr_onboarding_checklist_table_I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/hr_onboarding_checklist_table_I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/increase_indent_demo_id_paraid_overflow_insert_link_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/increase_indent_demo_id_paraid_overflow_insert_link_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/italic_and_underline_combo_style_default_missing_italic_subscript_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/italic_and_underline_combo_style_default_missing_italic_subscript_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/italic_subscript_demo_style_default_missing_italic_text_formatting_demo_id_paraid_overflow_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/italic_subscript_demo_style_default_missing_italic_text_formatting_demo_id_paraid_overflow_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/italic_text_formatting_demo_id_paraid_overflow_2_italic_text_formatting_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/italic_text_formatting_demo_id_paraid_overflow_2_italic_text_formatting_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/italic_text_formatting_demo_id_paraid_overflow_italic_underline_combined_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/italic_text_formatting_demo_id_paraid_overflow_italic_underline_combined_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/italic_underline_combined_demo_id_paraid_overflow_justified_underline_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/italic_underline_combined_demo_id_paraid_overflow_justified_underline_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/justified_underline_demo_id_paraid_overflow_justify_alignment_demo_id_paraid_overflow_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/justified_underline_demo_id_paraid_overflow_justify_alignment_demo_id_paraid_overflow_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/justify_alignment_demo_id_paraid_overflow_2_justify_alignment_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/justify_alignment_demo_id_paraid_overflow_2_justify_alignment_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/justify_alignment_demo_id_paraid_overflow_large_font_size_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/justify_alignment_demo_id_paraid_overflow_large_font_size_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/large_font_size_demo_id_paraid_overflow_left_alignment_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/large_font_size_demo_id_paraid_overflow_left_alignment_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/left_alignment_demo_id_paraid_overflow_line_spacing_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/left_alignment_demo_id_paraid_overflow_line_spacing_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/marketing_strategy_2026_suggesting_insertions_meeting_agenda_table_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/marketing_strategy_2026_suggesting_insertions_meeting_agenda_table_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/mcdoc_meeting_agenda_table_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/mcdoc_meeting_agenda_table_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/meeting_agenda_table_2_meeting_agenda_table_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/meeting_agenda_table_2_meeting_agenda_table_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/meeting_agenda_table_meeting_minutes_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/meeting_agenda_table_meeting_minutes_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/meeting_minutes_suggesting_insertions_multi_section_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/meeting_minutes_suggesting_insertions_multi_section_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/meeting_minutes_suggesting_insertions_numbered_list_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/meeting_minutes_suggesting_insertions_numbered_list_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/multi_section_nested_table_rowspan_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/multi_section_nested_table_rowspan_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/nested_table_rowspan_numbered_list_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/nested_table_rowspan_numbered_list_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/numbered_list_demo_id_paraid_overflow_numbered_list_italic_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/numbered_list_demo_id_paraid_overflow_numbered_list_italic_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/numbered_list_italic_demo_id_paraid_overflow_numwords_fldsimple_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/numbered_list_italic_demo_id_paraid_overflow_numwords_fldsimple_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/numbered_list_italic_demo_id_paraid_overflow_open_sans_bold_underline_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/numbered_list_italic_demo_id_paraid_overflow_open_sans_bold_underline_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/numwords_fldsimple_ole_object_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/numwords_fldsimple_ole_object_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/ole_object_ooxml_style_link_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/ole_object_ooxml_style_link_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/ooxml_style_link_open_sans_bold_underline_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/ooxml_style_link_open_sans_bold_underline_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/open_sans_bold_underline_id_paraid_overflow_open_sans_font_demo_id_paraid_overflow_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/open_sans_bold_underline_id_paraid_overflow_open_sans_font_demo_id_paraid_overflow_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/open_sans_font_demo_id_paraid_overflow_2_open_sans_font_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/open_sans_font_demo_id_paraid_overflow_2_open_sans_font_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/open_sans_font_demo_id_paraid_overflow_page_numbering_examples_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/open_sans_font_demo_id_paraid_overflow_page_numbering_examples_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/open_sans_font_demo_id_paraid_overflow_product_roadmap_2026_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/open_sans_font_demo_id_paraid_overflow_product_roadmap_2026_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/page_numbering_examples_potpourritest_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/page_numbering_examples_potpourritest_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/potpourritest_product_roadmap_2026_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/potpourritest_product_roadmap_2026_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/project_proposal_id_paraid_overflow_project_proposal_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/project_proposal_id_paraid_overflow_project_proposal_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/project_tasks_suggesting_insertions_q1_sales_summary_table_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/project_tasks_suggesting_insertions_q1_sales_summary_table_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/q1_sales_summary_table_2_q1_sales_summary_table_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/q1_sales_summary_table_2_q1_sales_summary_table_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/q1_sales_summary_table_quarterly_performance_report_table_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/q1_sales_summary_table_quarterly_performance_report_table_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/quarterly_performance_report_table_2_quarterly_performance_report_table_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/quarterly_performance_report_table_2_quarterly_performance_report_table_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/quarterly_performance_report_table_red_bold_heading_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/quarterly_performance_report_table_red_bold_heading_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/red_bold_heading_demo_style_default_missing_red_bold_text_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/red_bold_heading_demo_style_default_missing_red_bold_text_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/red_bold_text_demo_id_paraid_overflow_red_heading_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/red_bold_text_demo_id_paraid_overflow_red_heading_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/red_heading_demo_id_paraid_overflow_red_strikethrough_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/red_heading_demo_id_paraid_overflow_red_strikethrough_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/red_strikethrough_demo_style_default_missing_Redline_CiceroDo_v_plate_30_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/red_strikethrough_demo_style_default_missing_Redline_CiceroDo_v_plate_30_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/red_strikethrough_demo_style_default_missing_right_align_bold_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/red_strikethrough_demo_style_default_missing_right_align_bold_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/redline_cicerodo_v_plate_30_right_align_bold_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/redline_cicerodo_v_plate_30_right_align_bold_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/right_align_bold_demo_id_paraid_overflow_right_aligned_italic_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/right_align_bold_demo_id_paraid_overflow_right_aligned_italic_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/right_aligned_italic_demo_id_paraid_overflow_right_alignment_demo_id_paraid_overflow_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/right_aligned_italic_demo_id_paraid_overflow_right_alignment_demo_id_paraid_overflow_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/right_alignment_demo_id_paraid_overflow_2_right_alignment_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/right_alignment_demo_id_paraid_overflow_2_right_alignment_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/roboto_font_demo_id_paraid_overflow_2_roboto_font_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/roboto_font_demo_id_paraid_overflow_2_roboto_font_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/roboto_font_demo_id_paraid_overflow_roboto_underline_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/roboto_font_demo_id_paraid_overflow_roboto_underline_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/sample_document_afterword_repaired_word_repaired_sample_document_really_repaired_word_repaired_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/sample_document_afterword_repaired_word_repaired_sample_document_really_repaired_word_repaired_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/sample_document_really_repaired_word_repaired_sample_document_word_repair_of_our_output_iter2_word_repaired_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/sample_document_really_repaired_word_repaired_sample_document_word_repair_of_our_output_iter2_word_repaired_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/sample_document_word_repair_of_our_output_word_repaired_sd_2517_localized_heading_styles_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/sample_document_word_repair_of_our_output_word_repaired_sd_2517_localized_heading_styles_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/sample_document_word_repair_of_our_output_word_repaired_small_font_size_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/sample_document_word_repair_of_our_output_word_repaired_small_font_size_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/sd_2517_localized_heading_styles_sectpr_headerref_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/sd_2517_localized_heading_styles_sectpr_headerref_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/sectpr_headerref_single_paragraph_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/sectpr_headerref_single_paragraph_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/single_paragraph_small_font_size_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/single_paragraph_small_font_size_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/small_font_size_demo_id_paraid_overflow_strict01_sdt_controls_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/small_font_size_demo_id_paraid_overflow_strict01_sdt_controls_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/small_font_size_demo_id_paraid_overflow_strikethrough_and_italic_combo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/small_font_size_demo_id_paraid_overflow_strikethrough_and_italic_combo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/strict01_sdt_controls_Strict01_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/strict01_sdt_controls_Strict01_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/strict01_strikethrough_and_italic_combo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/strict01_strikethrough_and_italic_combo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/strikethrough_and_italic_combo_id_paraid_overflow_strikethrough_bold_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/strikethrough_and_italic_combo_id_paraid_overflow_strikethrough_bold_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/strikethrough_bold_demo_id_paraid_overflow_strikethrough_text_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/strikethrough_bold_demo_id_paraid_overflow_strikethrough_text_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/strikethrough_text_demo_id_paraid_overflow_strikethrough_text_formatting_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/strikethrough_text_demo_id_paraid_overflow_strikethrough_text_formatting_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/strikethrough_text_formatting_demo_id_paraid_overflow_subscript_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/strikethrough_text_formatting_demo_id_paraid_overflow_subscript_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/subscript_demo_id_paraid_overflow_subscript_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/subscript_demo_id_paraid_overflow_subscript_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/subscript_demo_style_default_missing_subtitle_style_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/subscript_demo_style_default_missing_subtitle_style_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/subtitle_style_demo_id_paraid_overflow_subtitle_style_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/subtitle_style_demo_id_paraid_overflow_subtitle_style_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/subtitle_style_demo_style_default_missing_superscript_demo_id_paraid_overflow_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/subtitle_style_demo_style_default_missing_superscript_demo_id_paraid_overflow_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/superscript_demo_id_paraid_overflow_2_superscript_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/superscript_demo_id_paraid_overflow_2_superscript_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/superscript_demo_id_paraid_overflow_superscript_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/superscript_demo_id_paraid_overflow_superscript_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/superscript_demo_style_default_missing_support_tickets_summary_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/superscript_demo_style_default_missing_support_tickets_summary_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/superscript_demo_style_default_missing_support_tickets_table_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/superscript_demo_style_default_missing_support_tickets_table_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/support_tickets_summary_id_paraid_overflow_support_tickets_table_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/support_tickets_summary_id_paraid_overflow_support_tickets_table_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/support_tickets_summary_id_paraid_overflow_text_highlight_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/support_tickets_summary_id_paraid_overflow_text_highlight_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/support_tickets_table_support_tickets_summary_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/support_tickets_table_support_tickets_summary_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/support_tickets_table_table_bookmark_end_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/support_tickets_table_table_bookmark_end_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/table_bookmark_end_table_vmerge_colspan_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/table_bookmark_end_table_vmerge_colspan_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/table_vmerge_colspan_text_box_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/table_vmerge_colspan_text_box_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/text_box_text_highlight_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/text_box_text_highlight_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/text_highlight_demo_style_default_missing_tiff_image_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/text_highlight_demo_style_default_missing_tiff_image_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/text_highlight_demo_style_default_missing_times_new_roman_bold_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/text_highlight_demo_style_default_missing_times_new_roman_bold_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/tiff_image_times_new_roman_bold_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/tiff_image_times_new_roman_bold_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/times_new_roman_bold_id_paraid_overflow_times_new_roman_font_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/times_new_roman_bold_id_paraid_overflow_times_new_roman_font_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/times_new_roman_font_id_paraid_overflow_title_style_centered_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/times_new_roman_font_id_paraid_overflow_title_style_centered_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/title_style_centered_demo_id_paraid_overflow_title_style_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/title_style_centered_demo_id_paraid_overflow_title_style_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/title_style_demo_id_paraid_overflow_title_style_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/title_style_demo_id_paraid_overflow_title_style_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/title_style_demo_style_default_missing_track_changes_editing_bullet_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/title_style_demo_style_default_missing_track_changes_editing_bullet_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/track_changes_editing_bullet_id_paraid_overflow_track_changes_editing_strikethrough_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/track_changes_editing_bullet_id_paraid_overflow_track_changes_editing_strikethrough_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/track_changes_editing_strikethrough_id_paraid_overflow_track_changes_suggesting_bold_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/track_changes_editing_strikethrough_id_paraid_overflow_track_changes_suggesting_bold_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/track_changes_suggesting_bold_id_paraid_overflow_track_changes_suggesting_calibri_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/track_changes_suggesting_bold_id_paraid_overflow_track_changes_suggesting_calibri_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/track_changes_suggesting_calibri_id_paraid_overflow_track_changes_suggesting_center_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/track_changes_suggesting_calibri_id_paraid_overflow_track_changes_suggesting_center_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/track_changes_suggesting_center_id_paraid_overflow_track_changes_suggesting_heading_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/track_changes_suggesting_center_id_paraid_overflow_track_changes_suggesting_heading_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/track_changes_suggesting_heading_id_paraid_overflow_track_changes_suggesting_italic_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/track_changes_suggesting_heading_id_paraid_overflow_track_changes_suggesting_italic_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/track_changes_suggesting_italic_id_paraid_overflow_track_changes_suggesting_title_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/track_changes_suggesting_italic_id_paraid_overflow_track_changes_suggesting_title_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/underline_text_demo_id_paraid_overflow_underline_text_formatting_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/underline_text_demo_id_paraid_overflow_underline_text_formatting_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/underline_text_formatting_demo_style_default_missing_verdana_bold_large_font_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/underline_text_formatting_demo_style_default_missing_verdana_bold_large_font_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_2_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_2_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/verdana_font_demo_id_paraid_overflow_2_verdana_font_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/verdana_font_demo_id_paraid_overflow_2_verdana_font_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/verdana_font_demo_id_paraid_overflow_verdana_italic_centered_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/verdana_font_demo_id_paraid_overflow_verdana_italic_centered_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/verdana_italic_centered_demo_id_paraid_overflow_vfdsdfcacawesd_suggesting_mixed_edits_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/verdana_italic_centered_demo_id_paraid_overflow_vfdsdfcacawesd_suggesting_mixed_edits_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/verdana_italic_centered_demo_id_paraid_overflow_word_clean_strict01_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/verdana_italic_centered_demo_id_paraid_overflow_word_clean_strict01_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/vfdsdfcacawesd_suggesting_mixed_edits_yellow_highlight_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/vfdsdfcacawesd_suggesting_mixed_edits_yellow_highlight_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/word_clean_strict01_word_tolerated_broken_media_rel_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/word_clean_strict01_word_tolerated_broken_media_rel_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/word_tolerated_broken_media_rel_word_tolerated_duplicate_ppr_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/word_tolerated_broken_media_rel_word_tolerated_duplicate_ppr_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/word_tolerated_duplicate_ppr_word_tolerated_misplaced_link_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/word_tolerated_duplicate_ppr_word_tolerated_misplaced_link_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/word_tolerated_misplaced_link_word_tolerated_misplaced_pgsz_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/word_tolerated_misplaced_link_word_tolerated_misplaced_pgsz_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/word_tolerated_misplaced_pgsz_word_tolerated_misplaced_uipriority_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/word_tolerated_misplaced_pgsz_word_tolerated_misplaced_uipriority_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/word_tolerated_misplaced_uipriority_word_tolerated_orphan_comment_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/word_tolerated_misplaced_uipriority_word_tolerated_orphan_comment_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/word_tolerated_orphan_comment_yellow_highlight_demo_id_paraid_overflow_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/word_tolerated_orphan_comment_yellow_highlight_demo_id_paraid_overflow_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_jubarte-rust_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/jubarte-rs-probe/pdf/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_jubarte-rust_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  set displayAlerts to true
end tell
