tell application "Microsoft Word"
  set displayAlerts to false
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/center_aligned_bold_text_id_paraid_overflow_center_alignment_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/center_aligned_bold_text_id_paraid_overflow_center_alignment_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/center_alignment_demo_id_paraid_overflow_2_center_alignment_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/center_alignment_demo_id_paraid_overflow_2_center_alignment_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/center_alignment_demo_id_paraid_overflow_center_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/center_alignment_demo_id_paraid_overflow_center_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/center_bold_demo_id_paraid_overflow_clear_formatting_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/center_bold_demo_id_paraid_overflow_clear_formatting_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/clear_formatting_demo_id_paraid_overflow_comments_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/clear_formatting_demo_id_paraid_overflow_comments_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/clear_formatting_demo_id_paraid_overflow_contract_review_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/clear_formatting_demo_id_paraid_overflow_contract_review_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/comments_complex_style_attr_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/comments_complex_style_attr_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/complex_style_attr_contract_review_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/complex_style_attr_contract_review_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/contract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/contract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/customer_satisfaction_survey_q4_suggesting_insertions_document_100_ultimate_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/document_100_ultimate_demo_id_paraid_overflow_docx_lots_of_comments_addition_redline_addition_v_removal_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/document_100_ultimate_demo_id_paraid_overflow_docx_lots_of_comments_addition_redline_addition_v_removal_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/document_100_ultimate_demo_id_paraid_overflow_double_spacing_bold_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/document_100_ultimate_demo_id_paraid_overflow_double_spacing_bold_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/docx_lots_of_comments_addition_docx_lots_of_comments_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/docx_lots_of_comments_addition_docx_lots_of_comments_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/docx_lots_of_comments_addition_redline_addition_v_removal_docx_lots_of_comments_addition_redline_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/docx_lots_of_comments_addition_redline_addition_v_removal_docx_lots_of_comments_addition_redline_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/docx_lots_of_comments_addition_redline_docx_lots_of_comments_addition_removal_redline_removal_v_addition_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/docx_lots_of_comments_addition_redline_docx_lots_of_comments_addition_removal_redline_removal_v_addition_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/docx_lots_of_comments_addition_removal_docx_lots_of_comments_addition_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/docx_lots_of_comments_addition_removal_docx_lots_of_comments_addition_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/docx_lots_of_comments_addition_removal_redline_docx_lots_of_comments_addition_removal_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/docx_lots_of_comments_addition_removal_redline_docx_lots_of_comments_addition_removal_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/docx_lots_of_comments_addition_removal_redline_removal_v_addition_docx_lots_of_comments_addition_removal_redline_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/docx_lots_of_comments_addition_removal_redline_removal_v_addition_docx_lots_of_comments_addition_removal_redline_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/docx_lots_of_comments_double_spacing_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/docx_lots_of_comments_double_spacing_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/double_spacing_bold_demo_id_paraid_overflow_eigenpal_docx_editor_suggesting_mixed_edits_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/double_spacing_bold_demo_id_paraid_overflow_eigenpal_docx_editor_suggesting_mixed_edits_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/eigenpal_docx_editor_suggesting_mixed_edits_employee_directory_table_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/eigenpal_docx_editor_suggesting_mixed_edits_employee_directory_table_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/employee_directory_table_2_employee_directory_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/employee_directory_table_2_employee_directory_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/employee_directory_table_employee_review_john_smith_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/employee_directory_table_employee_review_john_smith_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/employee_directory_table_employee_review_john_smith_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/employee_directory_table_employee_review_john_smith_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/employee_review_john_smith_suggesting_insertions_font_color_blue_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/employee_review_john_smith_suggesting_insertions_font_color_blue_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/font_color_blue_demo_style_default_missing_font_color_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/font_color_blue_demo_style_default_missing_font_color_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/font_color_demo_style_default_missing_font_family_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/font_color_demo_style_default_missing_font_family_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/font_family_demo_id_paraid_overflow_font_size_12_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/font_family_demo_id_paraid_overflow_font_size_12_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/font_size_12_demo_id_paraid_overflow_font_size_18_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/font_size_12_demo_id_paraid_overflow_font_size_18_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/font_size_18_demo_style_default_missing_font_size_24_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/font_size_18_demo_style_default_missing_font_size_24_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/font_size_24_demo_id_paraid_overflow_font_size_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/font_size_24_demo_id_paraid_overflow_font_size_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/font_size_demo_id_paraid_overflow_footnotes_sample_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/font_size_demo_id_paraid_overflow_footnotes_sample_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/font_size_demo_id_paraid_overflow_green_bold_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/font_size_demo_id_paraid_overflow_green_bold_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/footnotes_sample_gdocs_comments_export_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/footnotes_sample_gdocs_comments_export_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/gdocs_comments_export_green_bold_text_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/gdocs_comments_export_green_bold_text_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/green_bold_text_demo_id_paraid_overflow_green_highlight_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/green_bold_text_demo_id_paraid_overflow_green_highlight_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/green_highlight_demo_id_paraid_overflow_green_underline_bullet_list_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/green_highlight_demo_id_paraid_overflow_green_underline_bullet_list_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/green_underline_bullet_list_id_paraid_overflow_header_no_rels_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/green_underline_bullet_list_id_paraid_overflow_header_no_rels_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/green_underline_bullet_list_id_paraid_overflow_heading_1_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/green_underline_bullet_list_id_paraid_overflow_heading_1_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/header_no_rels_heading_1_bold_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/header_no_rels_heading_1_bold_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/heading_1_bold_demo_id_paraid_overflow_heading_1_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/heading_1_bold_demo_id_paraid_overflow_heading_1_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/heading_1_style_demo_id_paraid_overflow_heading_2_center_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/heading_1_style_demo_id_paraid_overflow_heading_2_center_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/heading_2_center_demo_id_paraid_overflow_heading_2_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/heading_2_center_demo_id_paraid_overflow_heading_2_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/heading_2_style_demo_id_paraid_overflow_heading_3_center_italic_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/heading_2_style_demo_id_paraid_overflow_heading_3_center_italic_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/heading_3_center_italic_id_paraid_overflow_heading_3_style_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/heading_3_center_italic_id_paraid_overflow_heading_3_style_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/heading_3_style_demo_id_paraid_overflow_2_heading_3_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/heading_3_style_demo_id_paraid_overflow_2_heading_3_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/heading_3_style_demo_id_paraid_overflow_heading_4_right_italic_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/heading_3_style_demo_id_paraid_overflow_heading_4_right_italic_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/heading_4_right_italic_id_paraid_overflow_heading_4_style_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/heading_4_right_italic_id_paraid_overflow_heading_4_style_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/heading_4_style_demo_id_paraid_overflow_2_heading_4_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/heading_4_style_demo_id_paraid_overflow_2_heading_4_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/heading_4_style_demo_id_paraid_overflow_helvetica_font_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/heading_4_style_demo_id_paraid_overflow_helvetica_font_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/helvetica_font_demo_style_default_missing_hr_onboarding_checklist_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/helvetica_font_demo_style_default_missing_hr_onboarding_checklist_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/hr_onboarding_checklist_table_I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/hr_onboarding_checklist_table_I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/increase_indent_demo_id_paraid_overflow_insert_link_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/increase_indent_demo_id_paraid_overflow_insert_link_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/insert_link_demo_id_paraid_overflow_inventory_list_suggesting_deletions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/inventory_list_suggesting_deletions_inventory_list_suggesting_mixed_edits_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/inventory_list_suggesting_mixed_edits_it_security_policy_v2_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/it_security_policy_v2_suggesting_insertions_italic_and_underline_combo_style_default_missing_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/italic_and_underline_combo_style_default_missing_italic_subscript_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/italic_and_underline_combo_style_default_missing_italic_subscript_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/italic_subscript_demo_style_default_missing_italic_text_formatting_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/italic_subscript_demo_style_default_missing_italic_text_formatting_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/italic_text_formatting_demo_id_paraid_overflow_2_italic_text_formatting_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/italic_text_formatting_demo_id_paraid_overflow_2_italic_text_formatting_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/italic_text_formatting_demo_id_paraid_overflow_italic_underline_combined_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/italic_text_formatting_demo_id_paraid_overflow_italic_underline_combined_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/italic_underline_combined_demo_id_paraid_overflow_justified_underline_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/italic_underline_combined_demo_id_paraid_overflow_justified_underline_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/justified_underline_demo_id_paraid_overflow_justify_alignment_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/justified_underline_demo_id_paraid_overflow_justify_alignment_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/justify_alignment_demo_id_paraid_overflow_2_justify_alignment_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/justify_alignment_demo_id_paraid_overflow_2_justify_alignment_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/justify_alignment_demo_id_paraid_overflow_large_font_size_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/justify_alignment_demo_id_paraid_overflow_large_font_size_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/large_font_size_demo_id_paraid_overflow_left_alignment_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/large_font_size_demo_id_paraid_overflow_left_alignment_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/left_alignment_demo_id_paraid_overflow_line_spacing_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/left_alignment_demo_id_paraid_overflow_line_spacing_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/line_spacing_demo_id_paraid_overflow_marketing_strategy_2026_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/marketing_strategy_2026_suggesting_insertions_meeting_agenda_table_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/marketing_strategy_2026_suggesting_insertions_meeting_agenda_table_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/mcdoc_meeting_agenda_table_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/mcdoc_meeting_agenda_table_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/meeting_agenda_table_2_meeting_agenda_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/meeting_agenda_table_2_meeting_agenda_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/meeting_agenda_table_meeting_minutes_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/meeting_agenda_table_meeting_minutes_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/meeting_minutes_id_paraid_overflow_meeting_minutes_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/meeting_minutes_suggesting_insertions_multi_section_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/meeting_minutes_suggesting_insertions_multi_section_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/meeting_minutes_suggesting_insertions_numbered_list_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/meeting_minutes_suggesting_insertions_numbered_list_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/multi_section_nested_table_rowspan_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/multi_section_nested_table_rowspan_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/nested_table_rowspan_numbered_list_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/nested_table_rowspan_numbered_list_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/numbered_list_demo_id_paraid_overflow_numbered_list_italic_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/numbered_list_demo_id_paraid_overflow_numbered_list_italic_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/numbered_list_italic_demo_id_paraid_overflow_numwords_fldsimple_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/numbered_list_italic_demo_id_paraid_overflow_numwords_fldsimple_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/numbered_list_italic_demo_id_paraid_overflow_open_sans_bold_underline_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/numbered_list_italic_demo_id_paraid_overflow_open_sans_bold_underline_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/numwords_fldsimple_ole_object_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/numwords_fldsimple_ole_object_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/ole_object_ooxml_style_link_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/ole_object_ooxml_style_link_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/ooxml_style_link_open_sans_bold_underline_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/ooxml_style_link_open_sans_bold_underline_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/open_sans_bold_underline_id_paraid_overflow_open_sans_font_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/open_sans_bold_underline_id_paraid_overflow_open_sans_font_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/open_sans_font_demo_id_paraid_overflow_2_open_sans_font_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/open_sans_font_demo_id_paraid_overflow_2_open_sans_font_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/open_sans_font_demo_id_paraid_overflow_page_numbering_examples_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/open_sans_font_demo_id_paraid_overflow_page_numbering_examples_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/open_sans_font_demo_id_paraid_overflow_product_roadmap_2026_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/open_sans_font_demo_id_paraid_overflow_product_roadmap_2026_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/page_numbering_examples_potpourritest_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/page_numbering_examples_potpourritest_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/potpourritest_product_roadmap_2026_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/potpourritest_product_roadmap_2026_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/product_roadmap_2026_suggesting_insertions_project_plan_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/project_plan_suggesting_insertions_project_proposal_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/project_proposal_id_paraid_overflow_project_proposal_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/project_proposal_id_paraid_overflow_project_proposal_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/project_proposal_suggesting_insertions_project_tasks_suggesting_insertions_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/project_tasks_suggesting_insertions_2_project_tasks_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/project_tasks_suggesting_insertions_q1_sales_summary_table_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/project_tasks_suggesting_insertions_q1_sales_summary_table_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/project_tasks_suggesting_insertions_q1_sales_summary_table_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/project_tasks_suggesting_insertions_q1_sales_summary_table_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/q1_sales_summary_table_2_q1_sales_summary_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/q1_sales_summary_table_2_q1_sales_summary_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/q1_sales_summary_table_quarterly_performance_report_table_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/q1_sales_summary_table_quarterly_performance_report_table_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/quarterly_performance_report_table_2_quarterly_performance_report_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/quarterly_performance_report_table_2_quarterly_performance_report_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/quarterly_performance_report_table_red_bold_heading_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/quarterly_performance_report_table_red_bold_heading_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/red_bold_heading_demo_style_default_missing_red_bold_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/red_bold_heading_demo_style_default_missing_red_bold_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/red_bold_text_demo_id_paraid_overflow_red_heading_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/red_bold_text_demo_id_paraid_overflow_red_heading_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/red_heading_demo_id_paraid_overflow_red_strikethrough_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/red_heading_demo_id_paraid_overflow_red_strikethrough_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/red_strikethrough_demo_style_default_missing_redline_cicerodo_v_plate_30_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/red_strikethrough_demo_style_default_missing_redline_cicerodo_v_plate_30_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/red_strikethrough_demo_style_default_missing_right_align_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/red_strikethrough_demo_style_default_missing_right_align_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/redline_cicerodo_v_plate_30_right_align_bold_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/redline_cicerodo_v_plate_30_right_align_bold_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/right_align_bold_demo_id_paraid_overflow_right_aligned_italic_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/right_align_bold_demo_id_paraid_overflow_right_aligned_italic_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/right_aligned_italic_demo_id_paraid_overflow_right_alignment_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/right_aligned_italic_demo_id_paraid_overflow_right_alignment_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/right_alignment_demo_id_paraid_overflow_2_right_alignment_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/right_alignment_demo_id_paraid_overflow_2_right_alignment_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/right_alignment_demo_id_paraid_overflow_risk_assessment_product_launch_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/risk_assessment_product_launch_suggesting_insertions_roboto_font_demo_id_paraid_overflow_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/roboto_font_demo_id_paraid_overflow_2_roboto_font_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/roboto_font_demo_id_paraid_overflow_2_roboto_font_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/roboto_font_demo_id_paraid_overflow_roboto_underline_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/roboto_font_demo_id_paraid_overflow_roboto_underline_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/roboto_underline_demo_id_paraid_overflow_sales_report_january_2026_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/sales_report_january_2026_suggesting_insertions_sample_document_afterword_repaired_word_repaired_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/sample_document_afterword_repaired_word_repaired_sample_document_really_repaired_word_repaired_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/sample_document_afterword_repaired_word_repaired_sample_document_really_repaired_word_repaired_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/sample_document_really_repaired_word_repaired_sample_document_word_repair_of_our_output_iter2_word_repaired_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/sample_document_really_repaired_word_repaired_sample_document_word_repair_of_our_output_iter2_word_repaired_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/sample_document_word_repair_of_our_output_iter2_word_repaired_sample_document_word_repair_of_our_output_word_repaired_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/sample_document_word_repair_of_our_output_word_repaired_sd_2517_localized_heading_styles_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/sample_document_word_repair_of_our_output_word_repaired_sd_2517_localized_heading_styles_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/sample_document_word_repair_of_our_output_word_repaired_small_font_size_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/sample_document_word_repair_of_our_output_word_repaired_small_font_size_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/sd_2517_localized_heading_styles_sectpr_headerref_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/sd_2517_localized_heading_styles_sectpr_headerref_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/sectpr_headerref_single_paragraph_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/sectpr_headerref_single_paragraph_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/single_paragraph_small_font_size_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/single_paragraph_small_font_size_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/small_font_size_demo_id_paraid_overflow_strict01_sdt_controls_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/small_font_size_demo_id_paraid_overflow_strict01_sdt_controls_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/small_font_size_demo_id_paraid_overflow_strikethrough_and_italic_combo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/small_font_size_demo_id_paraid_overflow_strikethrough_and_italic_combo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/strict01_sdt_controls_strict01_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/strict01_sdt_controls_strict01_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/strict01_strikethrough_and_italic_combo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/strict01_strikethrough_and_italic_combo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/strikethrough_and_italic_combo_id_paraid_overflow_strikethrough_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/strikethrough_and_italic_combo_id_paraid_overflow_strikethrough_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/strikethrough_bold_demo_id_paraid_overflow_strikethrough_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/strikethrough_bold_demo_id_paraid_overflow_strikethrough_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/strikethrough_text_demo_id_paraid_overflow_strikethrough_text_formatting_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/strikethrough_text_demo_id_paraid_overflow_strikethrough_text_formatting_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/strikethrough_text_formatting_demo_id_paraid_overflow_subscript_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/strikethrough_text_formatting_demo_id_paraid_overflow_subscript_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/subscript_demo_id_paraid_overflow_subscript_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/subscript_demo_id_paraid_overflow_subscript_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/subscript_demo_style_default_missing_subtitle_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/subscript_demo_style_default_missing_subtitle_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/subtitle_style_demo_id_paraid_overflow_subtitle_style_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/subtitle_style_demo_id_paraid_overflow_subtitle_style_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/subtitle_style_demo_style_default_missing_superscript_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/subtitle_style_demo_style_default_missing_superscript_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/superscript_demo_id_paraid_overflow_2_superscript_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/superscript_demo_id_paraid_overflow_2_superscript_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/superscript_demo_id_paraid_overflow_superscript_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/superscript_demo_id_paraid_overflow_superscript_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/superscript_demo_style_default_missing_support_tickets_summary_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/superscript_demo_style_default_missing_support_tickets_summary_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/superscript_demo_style_default_missing_support_tickets_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/superscript_demo_style_default_missing_support_tickets_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/support_tickets_summary_id_paraid_overflow_support_tickets_table_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/support_tickets_summary_id_paraid_overflow_support_tickets_table_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/support_tickets_summary_id_paraid_overflow_text_highlight_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/support_tickets_summary_id_paraid_overflow_text_highlight_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/support_tickets_table_support_tickets_summary_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/support_tickets_table_support_tickets_summary_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/support_tickets_table_table_bookmark_end_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/support_tickets_table_table_bookmark_end_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/table_bookmark_end_table_vmerge_colspan_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/table_bookmark_end_table_vmerge_colspan_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/table_vmerge_colspan_text_box_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/table_vmerge_colspan_text_box_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/text_box_text_highlight_demo_style_default_missing_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/text_box_text_highlight_demo_style_default_missing_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/text_highlight_demo_style_default_missing_tiff_image_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/text_highlight_demo_style_default_missing_tiff_image_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/text_highlight_demo_style_default_missing_times_new_roman_bold_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/text_highlight_demo_style_default_missing_times_new_roman_bold_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/tiff_image_times_new_roman_bold_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/tiff_image_times_new_roman_bold_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/times_new_roman_bold_id_paraid_overflow_times_new_roman_font_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/times_new_roman_bold_id_paraid_overflow_times_new_roman_font_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/times_new_roman_font_id_paraid_overflow_title_style_centered_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/times_new_roman_font_id_paraid_overflow_title_style_centered_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/title_style_centered_demo_id_paraid_overflow_title_style_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/title_style_centered_demo_id_paraid_overflow_title_style_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/title_style_demo_id_paraid_overflow_title_style_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/title_style_demo_id_paraid_overflow_title_style_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/title_style_demo_style_default_missing_track_changes_editing_bullet_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/title_style_demo_style_default_missing_track_changes_editing_bullet_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/track_changes_editing_bullet_id_paraid_overflow_track_changes_editing_strikethrough_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/track_changes_editing_bullet_id_paraid_overflow_track_changes_editing_strikethrough_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/track_changes_editing_strikethrough_id_paraid_overflow_track_changes_suggesting_bold_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/track_changes_editing_strikethrough_id_paraid_overflow_track_changes_suggesting_bold_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/track_changes_suggesting_bold_id_paraid_overflow_track_changes_suggesting_calibri_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/track_changes_suggesting_bold_id_paraid_overflow_track_changes_suggesting_calibri_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/track_changes_suggesting_calibri_id_paraid_overflow_track_changes_suggesting_center_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/track_changes_suggesting_calibri_id_paraid_overflow_track_changes_suggesting_center_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/track_changes_suggesting_center_id_paraid_overflow_track_changes_suggesting_heading_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/track_changes_suggesting_center_id_paraid_overflow_track_changes_suggesting_heading_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/track_changes_suggesting_heading_id_paraid_overflow_track_changes_suggesting_italic_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/track_changes_suggesting_heading_id_paraid_overflow_track_changes_suggesting_italic_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/track_changes_suggesting_italic_id_paraid_overflow_track_changes_suggesting_title_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/track_changes_suggesting_italic_id_paraid_overflow_track_changes_suggesting_title_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/track_changes_suggesting_title_id_paraid_overflow_training_materials_onboarding_program_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/training_materials_onboarding_program_suggesting_insertions_underline_text_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/underline_text_demo_id_paraid_overflow_underline_text_formatting_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/underline_text_demo_id_paraid_overflow_underline_text_formatting_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/underline_text_formatting_demo_style_default_missing_verdana_bold_large_font_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/underline_text_formatting_demo_style_default_missing_verdana_bold_large_font_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_2_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_2_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/verdana_bold_large_font_id_paraid_overflow_verdana_font_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/verdana_font_demo_id_paraid_overflow_2_verdana_font_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/verdana_font_demo_id_paraid_overflow_2_verdana_font_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/verdana_font_demo_id_paraid_overflow_verdana_italic_centered_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/verdana_font_demo_id_paraid_overflow_verdana_italic_centered_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/verdana_italic_centered_demo_id_paraid_overflow_vfdsdfcacawesd_suggesting_mixed_edits_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/verdana_italic_centered_demo_id_paraid_overflow_vfdsdfcacawesd_suggesting_mixed_edits_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/verdana_italic_centered_demo_id_paraid_overflow_word_clean_strict01_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/verdana_italic_centered_demo_id_paraid_overflow_word_clean_strict01_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/vfdsdfcacawesd_suggesting_mixed_edits_yellow_highlight_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/vfdsdfcacawesd_suggesting_mixed_edits_yellow_highlight_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/word_clean_strict01_word_tolerated_broken_media_rel_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/word_clean_strict01_word_tolerated_broken_media_rel_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/word_tolerated_broken_media_rel_word_tolerated_duplicate_ppr_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/word_tolerated_broken_media_rel_word_tolerated_duplicate_ppr_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/word_tolerated_duplicate_ppr_word_tolerated_misplaced_link_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/word_tolerated_duplicate_ppr_word_tolerated_misplaced_link_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/word_tolerated_misplaced_link_word_tolerated_misplaced_pgsz_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/word_tolerated_misplaced_link_word_tolerated_misplaced_pgsz_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/word_tolerated_misplaced_pgsz_word_tolerated_misplaced_uipriority_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/word_tolerated_misplaced_pgsz_word_tolerated_misplaced_uipriority_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/word_tolerated_misplaced_uipriority_word_tolerated_orphan_comment_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/word_tolerated_misplaced_uipriority_word_tolerated_orphan_comment_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/word_tolerated_orphan_comment_yellow_highlight_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/word_tolerated_orphan_comment_yellow_highlight_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/yellow_highlight_demo_id_paraid_overflow_yellow_highlight_italic_demo_style_default_missing_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$5_line_spacing_id_paraid_overflow_24_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$5_line_spacing_id_paraid_overflow_24_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$_id_paraid_overflow_alternate_content_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$_id_paraid_overflow_alternate_content_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$_id_paraid_overflow_blue_bold_centered_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$_id_paraid_overflow_blue_bold_centered_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_increase_indent_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you_increase_indent_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$dget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$dget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$dget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$dget_report_q1_2026_suggesting_insertions_bullet_list_bold_demo_id_paraid_overflow_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ear_formatting_demo_id_paraid_overflow_comments_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ear_formatting_demo_id_paraid_overflow_comments_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ear_formatting_demo_id_paraid_overflow_contract_review_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ear_formatting_demo_id_paraid_overflow_contract_review_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ld_and_italic_combo_style_default_missing_bold_and_underline_combo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ld_and_italic_combo_style_default_missing_bold_and_underline_combo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ld_and_underline_combo_id_paraid_overflow_bold_italic_combined_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ld_and_underline_combo_id_paraid_overflow_bold_italic_combined_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ld_italic_combined_demo_id_paraid_overflow_bold_italic_underline_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ld_italic_combined_demo_id_paraid_overflow_bold_italic_underline_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ld_italic_underline_demo_id_paraid_overflow_bold_red_text_combo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ld_italic_underline_demo_id_paraid_overflow_bold_red_text_combo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ld_red_text_combo_id_paraid_overflow_bold_superscript_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ld_red_text_combo_id_paraid_overflow_bold_superscript_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ld_superscript_demo_style_default_missing_bold_text_formatting_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ld_superscript_demo_style_default_missing_bold_text_formatting_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ld_text_formatting_demo_id_paraid_overflow_2_bold_text_formatting_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ld_text_formatting_demo_id_paraid_overflow_2_bold_text_formatting_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ld_text_formatting_demo_id_paraid_overflow_bold_underline_combined_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ld_text_formatting_demo_id_paraid_overflow_bold_underline_combined_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ld_underline_combined_demo_id_paraid_overflow_bold_underline_highlight_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ld_underline_combined_demo_id_paraid_overflow_bold_underline_highlight_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ld_underline_highlight_demo_id_paraid_overflow_book_catalog_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ld_underline_highlight_demo_id_paraid_overflow_book_catalog_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$libri_bold_italic_demo_id_paraid_overflow_calibri_font_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$libri_bold_italic_demo_id_paraid_overflow_calibri_font_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$libri_font_demo_id_paraid_overflow_2_calibri_font_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$libri_font_demo_id_paraid_overflow_2_calibri_font_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$libri_font_demo_id_paraid_overflow_calibri_heading_2_right_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$libri_font_demo_id_paraid_overflow_calibri_heading_2_right_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$libri_heading_2_right_id_paraid_overflow_center_aligned_bold_text_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$libri_heading_2_right_id_paraid_overflow_center_aligned_bold_text_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$llet_list_bold_demo_id_paraid_overflow_bullet_list_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$llet_list_bold_demo_id_paraid_overflow_bullet_list_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$llet_list_demo_id_paraid_overflow_calibri_bold_italic_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$llet_list_demo_id_paraid_overflow_calibri_bold_italic_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$mments_complex_style_attr_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$mments_complex_style_attr_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$mplex_style_attr_contract_review_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$mplex_style_attr_contract_review_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$nter_aligned_bold_text_id_paraid_overflow_center_alignment_demo_id_paraid_overflow_2_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$nter_aligned_bold_text_id_paraid_overflow_center_alignment_demo_id_paraid_overflow_2_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$nter_alignment_demo_id_paraid_overflow_2_center_alignment_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$nter_alignment_demo_id_paraid_overflow_2_center_alignment_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$nter_alignment_demo_id_paraid_overflow_center_bold_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$nter_alignment_demo_id_paraid_overflow_center_bold_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$nter_bold_demo_id_paraid_overflow_clear_formatting_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$nter_bold_demo_id_paraid_overflow_clear_formatting_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ntract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ntract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ntract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ntract_review_suggesting_insertions_contract_review_suggesting_mixed_edits_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ntract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ntract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ntract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ntract_review_suggesting_mixed_edits_customer_satisfaction_survey_q4_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ok_catalog_id_paraid_overflow_book_catalog_table_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ok_catalog_id_paraid_overflow_book_catalog_table_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ok_catalog_table_budget_report_q1_2026_suggesting_insertions_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ok_catalog_table_budget_report_q1_2026_suggesting_insertions_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ok_catalog_table_budget_report_q1_2026_suggesting_insertions_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ok_catalog_table_budget_report_q1_2026_suggesting_insertions_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ternate_content_anchor_images_word_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ternate_content_anchor_images_word_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ue_bold_centered_demo_id_paraid_overflow_blue_centered_title_demo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ue_bold_centered_demo_id_paraid_overflow_blue_centered_title_demo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ue_centered_title_demo_style_default_missing_blue_italic_text_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ue_centered_title_demo_style_default_missing_blue_italic_text_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ue_italic_text_demo_id_paraid_overflow_blue_underline_combo_demo_id_paraid_overflow_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ue_italic_text_demo_id_paraid_overflow_blue_underline_combo_demo_id_paraid_overflow_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  try
    open POSIX file "/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_redlines_word/~$ue_underline_combo_demo_id_paraid_overflow_bold_and_italic_combo_style_default_missing_redline.docx"
    set theDoc to active document
    save as theDoc file name "/Users/arthrod/temp/T/neurotic_docx_bench/sanity_word/sanity_pdf_redlines_word/~$ue_underline_combo_demo_id_paraid_overflow_bold_and_italic_combo_style_default_missing_redline.pdf" file format format PDF
    close theDoc saving no
  on error
    try
      close every document saving no
    end try
  end try
  set displayAlerts to true
end tell