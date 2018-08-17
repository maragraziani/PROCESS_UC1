Data structure:

The following folders contain the original bigTIFF files from Camelyon17. *
center_0
center_1
center_3
center_2
center_4

* NOTE: The files are too big to be uploaded on BitBucket. To run the code you should download the bigTIFF from here: https://camelyon17.grand-challenge.org/data/ and collocate them in the respective folders. 

lesion_annotations contains the XML files with the annotations of the WSIs.

intermediate_datasets contains the H5DB files we create in the patch extraction module. NOTE: These files are generated by us. I have just introduced a mock database with very few entries to keep the size limited. I recommend to first extract the patches and then use the generated files to run the training. 