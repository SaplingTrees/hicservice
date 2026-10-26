# CATAD

***CATAD is a method to identify topologically associating domains from Hi-C datasets based on a Core-attachment Structure.



## Requirements

enviorment : Python3.7 or above.

packages : including numpy,pandas,scipy and portion using pip or conda.



## Usage


python CATAD.py input_Hi_C_i CS_threshold output_TAD_i


###Parameters

```
input_Hi_C_i : the input file of a N*N Hi-C matrix separated by TAB for a chromosome i.

CS_threshold : the threshold for cosion similarity. (Default value is 0.8)

output_TAD_i : the output file for the predicted TAD of chromosome i, in which a line represents a TAD containing two columns that represent the start bin and the end bin of a TAD.



## Notes

This tool requires only a single user-defined parameter **CS_threthold**, which enable users to use easily. The default value of this parameter is 0.8.




