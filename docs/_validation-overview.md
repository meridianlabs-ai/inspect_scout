When developing scanners and scanner prompts, it's often desirable to create a feedback loop based on some ground truth regarding the ideal results that should by yielded by scanner. You can do this by creating a validation set and applying it during your scan.

When you run a scan, Scout View will show validation results alongside scanner values (sorting validated scans to the top for easy review):

![](images/validation.png){.border}

Note that the overall validation score is also displayed in the left panel summarizing the scan. Below we'll go step by step through how to create a validation set and apply it to your scanners.