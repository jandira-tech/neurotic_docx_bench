# Correction: read-only fixture staging invalidated the Word compare exclusions

The original fixture-copy helper preserved mode 0444 from the Hugging Face cache. The repository Word script then preserved that mode with copy2 when staging inside Word. All 30 original compare-message failures had read-only bases, and none of the original read-only bases succeeded. This was a benchmark setup error. The earlier claim that those files were corrupt is withdrawn.

The patched inline/ready diagnostic wrappers are abandoned. Word is now driven only by the unmodified repository CLI. Writable copies use mode 0644 and are verified byte-for-byte against the frozen original manifest. The original failed cohort is rechecked before any vendor runs. The many earlier reserve rounds are diagnostic attempts, not the authoritative fixture selection.
