# DSC630 Fall 2020 - Term Project
# Team: Torrey Capobianco, Conrad Ibanez , Edris Safari 

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import group3lib as g3lib

# Set the random seed
np.random.seed(3)   

def main():
    
    marketing_data_df = g3lib.read_file2()
    print(marketing_data_df.head())
    g3lib.create_scatterplots(marketing_data_df)
    
    g3lib.createStatisticsHeatmap(marketing_data_df)
    
    g3lib.evaluate_kmeans(marketing_data_df)
    
    #g3lib.perform_reduction_analysis(marketing_data_df)
 
if __name__ == '__main__':
    main()
    
